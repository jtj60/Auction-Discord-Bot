import asyncio
from logging import log
import os

from dotenv import load_dotenv

# This has to come first because it patches the env, and the replit-db looks for REPLIT_DB_URL in the env
load_dotenv()
import discord
from discord.ext import commands
from discord.enums import ChannelType
from replit import db
from transitions import Machine
from log_utils import log_command
from log_utils import command_log

from draft import Auction, AuctionValidationError, ClientMessageType
from draft import ADMIN_IDS
import embed
import playerlist_util
from lot import Lot
from keep_alive import keep_alive

intents = discord.Intents.default()
intents.members = True
client = commands.Bot(command_prefix='!', intents=intents)


class UserType:
    CAPTAIN = 1
    PLAYER = 2
    ADMIN = 3
    ANY = 4


GENERIC_DRAFT_CHANNEL_NAMES = [
    "draft",
    "draft-channel",
    "draft-chat",
    "testing-channel",
    "test-channel",
    "player-draft",
    "mock-draft"
]


@client.event
async def on_ready():
    print("Bot is ready.")


class NominationTimer:
    def __init__(self, t, captain_name, ctx):
        self.t = t
        self.captain_name = captain_name
        self.ctx = ctx
        self.cancelled = False
        self.paused = False

    async def run(self):
        players_to_nom = db["players"]
        await self.ctx.send(embed = embed.playerlist(players_to_nom))
        await self.ctx.send(
            embed = embed.display_transition_to_nomination(
                self.captain_name, 
                CAPTAIN_NOMINATION_TIMEOUT,
            )
        )
        user = AuctionBot.get_mention(self.captain_name)
        await self.ctx.send(user.mention)
        for i in range(self.t, 0, -1):
            while self.paused:
                await asyncio.sleep(1)

            if self.cancelled:
                raise asyncio.CancelledError()

            await asyncio.sleep(1)
            if i == 10:
                await self.ctx.send(
                    f"{self.captain_name} has {i} seconds left to nominate a player."
                )
            if i == 5:
                await self.ctx.send(
                    f"{self.captain_name} has {i} seconds left to nominate a player."
                )

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def cancel(self):
        self.cancelled = True


CAPTAIN_NOMINATION_TIMEOUT = 45
BUFFER_TIMER = 10
BREAK_TIMER = 60
NUMBER_OF_ROUNDS = 4


class AuctionBot(commands.Cog):
    def __init__(self, client, debug=False):
        self.emojis = {
            "check": "<:green_checkmark:920049176967020554>",  # check for bot reaction
            "red x": "<:red_x:920046598367621180>",  # red x for bot reaction
            "plus": "👍",  # plus for bot reaction
            "minus": "👎",  # minus for bot reaction
        }

        self.client = client
        self.current_timer = None
        self.debug = debug
        self.auction = Auction()
        self.starting_context = None

    def rotateCaptainList(self):
        self.captains = db["captains"]
        cap = self.captains[0]
        self.captains.append(cap)
        self.captains.pop(0)
        db["captains"] = self.captains

    def clearCaptains(self):
        self.captains.clear()
        db["captains"] = self.captains

    def is_admin(self, ctx):
        if ctx.message.author.id in ADMIN_IDS or self.debug:
            return True
        return False
    
    def get_mention(name):
        members = client.get_all_members()
        user = discord.utils.get(members, name=name)
        return user

    def whitelist(self, ctx, dm=None, channel=None, channel_names=None):
        if dm is None:
            dm = []
        if channel is None:
            channel = []
        if channel_names is None:
            channel_names = []

        message_channel = ctx.channel
        author = ctx.message.author
        if message_channel.type == ChannelType.private:
            # Is DM
            if UserType.ANY in dm:
                return True
            elif self.is_admin(ctx) and UserType.ADMIN in dm:
                return True
            elif (
                self.auction.search_captain(author.name) is not None
                and UserType.CAPTAIN in dm
            ):
                return True
            elif (
                self.auction.search_player(author.name) is not None
                and UserType.PLAYER in dm
            ):
                return True
            return False

        if (
            message_channel.type == ChannelType.text
            and message_channel.name in channel_names
        ):
            if UserType.ANY in channel:
                return True
            elif self.is_admin(ctx) and UserType.ADMIN in channel:
                return True
            elif (
                self.auction.search_captain(author.name) is not None
                and UserType.CAPTAIN in channel
            ):
                return True
            elif (
                self.auction.search_player(author.name) is not None
                and UserType.PLAYER in channel
            ):
                return True
            return False

        return False
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel == self.starting_context.channel:
            if self.auction.machine.state == "buffering" or self.auction.machine.state == 'break':                                                
                if message.author.id in ADMIN_IDS:                                      # can't use whitelist method, on_message takes a message object, not ctx
                    return
                else:
                    await message.delete()

    @commands.command()
    async def start(self, ctx):
        self.starting_context = ctx
        log_command(ctx)
        if not self.whitelist(
            ctx, channel=[UserType.ADMIN], channel_names=GENERIC_DRAFT_CHANNEL_NAMES
        ):
            return
        try:
            client_message = self.auction.start(ctx.message)
            await ctx.send(client_message.data)
        except AuctionValidationError as e:
            if e.client_message.type == ClientMessageType.CHANNEL_MESSAGE:
                await ctx.send(e.client_message.data)
        await self._transition_to_nominating_and_start_timer(ctx)

    def _name_with_discriminator(self, author):
        return author.name + "#" + author.discriminator

    @commands.command()
    async def checkin(self, ctx):
        log_command(ctx)
        if not self.whitelist(
            ctx, channel=[UserType.ADMIN, UserType.CAPTAIN], channel_names=GENERIC_DRAFT_CHANNEL_NAMES
        ):
            await ctx.message.add_reaction(self.emojis["minus"])
            author = ctx.message.author
            print(11111, author.name, author.display_name, author.id)
            return
        await ctx.message.add_reaction(self.emojis["plus"])

    async def _nominate(self, ctx):
        try:
            new_lot = self.auction.nominate(ctx.message)
        except AuctionValidationError as e:
            await ctx.send(e.client_message.data)
            return None

        # Someone was waiting on a successful nomination, let them know it's done
        if self.current_timer is not None:
            self.current_timer.cancel()
            self.current_timer = None

        return new_lot

    async def _transition_to_nominating_and_start_timer(self, ctx):
        if self.auction.machine.state == 'starting':
            self.auction.machine.nom_from_start()
        elif self.auction.machine.state == 'bidding':
            self.auction.machine.nom_from_bid()
        next_captain = self.auction.get_next_captain()
        if next_captain is None:
            await ctx.send("All done. *Throne exploding noises*")
            return
        self.current_timer = NominationTimer(
            CAPTAIN_NOMINATION_TIMEOUT, next_captain['name'], ctx
        )
        try:
            await self.current_timer.run()
            new_lot = self.auction.autonominate(next_captain)
            await ctx.send(
                f"Timer expired. Auto-nominator has nominated {new_lot.player} on behalf of {new_lot.nominator}"
            )
            await self._run_lot(ctx)
        except asyncio.CancelledError:
            return
    
    async def buffer(self):
        self.auction.machine.buff_from_nom()
        await asyncio.sleep(BUFFER_TIMER)
        self.auction.machine.bid_from_buff()
    
    async def take_break(self, ctx):
        self.auction.machine.break_from_nom()  
        await ctx.send(embed=embed.display_break(BREAK_TIMER))
        await asyncio.sleep(5)
        
        teams = self.auction.get_current_teams()
        for captains, players in teams.items():
            captain = self.auction.search_captain(captains)
            bank = captain["dollars"]
            await ctx.send(embed = embed.display_team(captains, bank, players))
        await ctx.send(embed=embed.playerlist(self.auction.players))
        
        await asyncio.sleep(BREAK_TIMER)
        self.auction.machine.nom_from_break()

    async def _run_lot(self, ctx):
        # We have a nomination, run the lot
        player_name = self.auction.current_lot.player 
        captain_name = self.auction.current_lot.nominator
        print(f"Starting lot {self.auction.current_lot.to_dict()}")

        await ctx.send(
            embed=embed.display_successful_nomination(
                self.auction.search_player(player_name),
                self.auction.search_captain(captain_name),
                BUFFER_TIMER
            )
        )
        await ctx.send(embed=embed.captainlist(self.auction.captains))
        await ctx.send(
            embed=embed.player_info(
                self.auction.search_player(player_name)
            )
        )

        await self.buffer()

        for time_remaining in self.auction.run_current_lot():
            await asyncio.sleep(1)
            if time_remaining is None:
                continue
            if time_remaining > 0 and time_remaining % 5 == 0:
                await ctx.send(
                    f"{time_remaining} seconds left for player {player_name}"
                )
        nomination = self.auction.give_lot_to_winner()
        await ctx.send(
            embed=embed.winning_bid(nomination)
        )
        nom_break = len(self.auction.db["players"])/NUMBER_OF_ROUNDS
        if len(self.auction.db["nominations"]) % nom_break == 0 and len(self.auction.db["nominations"]) > 0:
            await self.take_break(ctx)
        
        # Yes, this is intentionally recursive. The idea is that the auction
        # should be able to run itself without human input.
        await self._transition_to_nominating_and_start_timer(ctx)

    @commands.command()
    async def nominate(self, ctx):
        log_command(ctx)

        if not self.whitelist(
            ctx,
            channel=[UserType.ADMIN, UserType.CAPTAIN],
            channel_names=GENERIC_DRAFT_CHANNEL_NAMES,
        ):
            return
        try:
            new_lot = await self._nominate(ctx)
            if new_lot is None:
                if self.auction.machine.state == 'nominating' and self.current_timer is None:
                    print("Invalid nomination and no autonom timer")
                    command_log.warning(
                        "Invalid nomination and no autonom timer",
                    )
                return
            await self._run_lot(ctx)

        except asyncio.CancelledError:
            print("Nomination timer cancelled successfully")
            pass

    @commands.command()
    async def bid(self, ctx):
        log_command(ctx)
        if not self.whitelist(
            ctx,
            channel=[UserType.ADMIN, UserType.CAPTAIN],
            channel_names=GENERIC_DRAFT_CHANNEL_NAMES,
        ):
            return
        try:
            time_remaining = self.auction.bid(ctx.message)
            if time_remaining is not None:
                await ctx.message.add_reaction(self.emojis["plus"])
                await ctx.send(f"{time_remaining} seconds left after latest bid.")
        except AuctionValidationError as e:
            if e.client_message.type == ClientMessageType.CHANNEL_MESSAGE:
                await ctx.send(e.client_message.data)
                await ctx.message.add_reaction(self.emojis["minus"])
            return None

    @commands.command()
    async def pause(self, ctx):
        log_command(ctx)
        #TODO: print out context like current captain if nomination state, or current player if bid state
        if not self.whitelist(
            ctx, channel=[UserType.ADMIN], channel_names=GENERIC_DRAFT_CHANNEL_NAMES
        ):
            return
        if self.auction.machine.state == "nominating":
            self.current_timer.pause()
            await ctx.send("Nomination timer paused.")
        elif self.auction.machine.state == "bidding":
            self.auction.current_lot.is_paused = True
            await ctx.send("Bidding timer paused.")

    @commands.command()
    async def resume(self, ctx):
        log_command(ctx)
        #TODO: print out context like current captain if nomination state, or current player if bid state
        if not self.whitelist(
            ctx, channel=[UserType.ADMIN], channel_names=GENERIC_DRAFT_CHANNEL_NAMES
        ):
            return
        if self.auction.machine.state == "nominating":
            self.current_timer.resume()
            await ctx.send("Nomination timer resumed.")
        elif self.auction.machine.state == "bidding":
            self.auction.current_lot.is_paused = False
            await ctx.send("Bidding timer resumed.")

    @commands.command()
    async def playerlist(self, ctx):
        log_command(ctx)
        if not self.whitelist(
            ctx,
            dm=[UserType.ADMIN],
            channel=[UserType.ADMIN],
            channel_names=GENERIC_DRAFT_CHANNEL_NAMES,
        ):
            return
        await ctx.send(embed=embed.playerlist(self.auction.players))

    @commands.command()
    async def captainlist(self, ctx):
        log_command(ctx)
        if not self.whitelist(
            ctx,
            dm=[UserType.ADMIN],
            channel=[UserType.ADMIN],
            channel_names=GENERIC_DRAFT_CHANNEL_NAMES,
        ):
            return
        await ctx.send(embed=embed.captainlist(self.auction.captains))

    @commands.command()
    async def playerinfo(self, ctx):
        log_command(ctx)
        if not self.whitelist(
            ctx,
            dm=[UserType.ADMIN],
            channel=[UserType.ADMIN],
            channel_names=GENERIC_DRAFT_CHANNEL_NAMES,
        ):
            return
        await ctx.send(embed=embed.player_info(ctx.message))

    @commands.command()
    async def player(self, ctx):
        log_command(ctx)
        if not self.whitelist(
            ctx,
            dm=[UserType.ADMIN],
            channel=[UserType.ADMIN],
            channel_names=GENERIC_DRAFT_CHANNEL_NAMES,
        ):
            return
        try:
            self.auction.player(ctx.message)
            await ctx.message.add_reaction(self.emojis["plus"])
        except AuctionValidationError as e:
            if e.client_message.type == ClientMessageType.CHANNEL_MESSAGE:
                await ctx.send(e.client_message.data)
                await ctx.message.add_reaction(self.emojis["minus"])

    @commands.command()
    async def captain(self, ctx):
        log_command(ctx)
        if not self.whitelist(
            ctx,
            dm=[UserType.ADMIN],
            channel=[UserType.ADMIN],
            channel_names=GENERIC_DRAFT_CHANNEL_NAMES,
        ):
            return
        try:
            self.auction.captain(ctx.message)
            await ctx.message.add_reaction(self.emojis["plus"])
        except AuctionValidationError as e:
            if e.client_message.type == ClientMessageType.CHANNEL_MESSAGE:
                await ctx.send(e.client_message.data)
                await ctx.message.add_reaction(self.emojis["minus"])

    @commands.command()
    async def upload_test_lists(self, ctx):
        log_command(ctx)
        if not self.whitelist(
            ctx,
            dm=[UserType.ADMIN],
            channel=[UserType.ADMIN],
            channel_names=GENERIC_DRAFT_CHANNEL_NAMES,
        ):
            return
        self.auction.bootstrap_from_testlists()
        await ctx.send("Test lists uploaded")

    @commands.command()
    async def DELETE(self, ctx):
        log_command(ctx)
        if not self.whitelist(
            ctx,
            dm=[UserType.ADMIN],
            channel=[UserType.ADMIN],
            channel_names=GENERIC_DRAFT_CHANNEL_NAMES,
        ):
            return

        await ctx.send("Are you sure you want to delete the database? y or n.")

        def check(msg):
            return (
                msg.author == ctx.author
                and msg.channel == ctx.channel
                and msg.content.lower() in ["y", "n"]
            )

        msg = await client.wait_for("message", check=check)
        if msg.content.lower() == "y":
            self.auction.delete_db()
            await ctx.send("Database deleted.")
        elif msg.content.lower() == "n":
            await ctx.send("Databases not deleted.")
    
    @commands.command()
    async def teams(self, ctx):
        log_command(ctx)
        if not self.whitelist(
            ctx,
            dm=[UserType.ADMIN],
            channel=[UserType.ADMIN],
            channel_names=GENERIC_DRAFT_CHANNEL_NAMES,
        ):
            return
        teams = self.auction.get_current_teams()
        for captains, players in teams.items():
            captain = self.auction.search_captain(captains)
            bank = captain["dollars"]
            await ctx.send(embed = embed.display_team(captains, bank, players))

# keep_alive()
if __name__ == "__main__":
    client.add_cog(AuctionBot(client))

    # BOT TOKEN
    client.run(os.getenv("DISCORD_AUTH_TOKEN"))

