import asyncio
from logging import log
import os

from dotenv import load_dotenv

# This has to come first because it patches the env, and the replit-db looks for REPLIT_DB_URL in the env
load_dotenv()
from discord.ext import commands
from discord.enums import ChannelType
from replit import db
from transitions import Machine
from log_utils import log_command

from draft import Auction, AuctionValidationError, ClientMessageType
from draft import ADMIN_IDS
import embed
import playerlist_util
from lot import Lot
from keep_alive import keep_alive

client = commands.Bot(command_prefix="$")


class UserType:
    CAPTAIN = 1
    PLAYER = 2
    ADMIN = 3
    ANY = 4


GENERIC_DRAFT_CHANNEL_NAMES = [
    "draft",
    "draft-channel",
    "draft-chat",
    "general",
    "testing-channel",
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


CAPTAIN_NOMINATION_TIMEOUT = 30


class AuctionBot(commands.Cog):
    def __init__(self, client, debug=False):
        self.start = 10  # enter start timer
        self.nom = 30  # enter nominating timer
        self.bid = 60  # enter bidding timer
        self.league = "PST"  # enter league name
        self.emojis = {
            "check": "<:green_checkmark:920049176967020554>",  # check for bot reaction
            "red x": "<:red_x:920046598367621180>",  # red x for bot reaction
        }

        self.client = client
        self.current_timer = None
        self.debug = debug
        self.auction = Auction()

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

    @commands.command()
    async def start(self, ctx):
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
                await ctx.send("Invalid nomination, will default to autonom")
                if self.current_timer is None:
                    next_elibible_captain = self.auction.get_next_captain()
                    self.current_timer = NominationTimer(
                        CAPTAIN_NOMINATION_TIMEOUT, next_elibible_captain["name"], ctx
                    )
                    await self.current_timer.run()
                    self.current_timer = None
                    new_lot = self.auction.autonominate(next_elibible_captain)
                    await ctx.send(
                        f"Timer expired. Auto-nominator has nominated {new_lot.player} on behalf of {new_lot.nominator}"
                    )


            # We have a nomination, run the lot
            player_name = self.auction.current_lot.player
            print(f"Starting lot {self.auction.current_lot.to_dict()}")
            await ctx.send(
                embed=embed.player_info(self.auction.search_player(player_name))
            )
            for time_remaining in self.auction.run_current_lot():
                await asyncio.sleep(1)
                if time_remaining is None:
                    continue
                if time_remaining > 0 and time_remaining % 10 == 0:
                    await ctx.send(
                        f"{time_remaining} seconds left for player {player_name}"
                    )
            self.auction.give_lot_to_winner()

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
            flag = self.auction.bid(ctx.message)
            if flag is not None:
                await ctx.message.add_reaction(self.emojis["check"])
        except AuctionValidationError as e:
            if e.client_message.type == ClientMessageType.CHANNEL_MESSAGE:
                await ctx.send(e.client_message.data)
                await ctx.message.add_reaction(self.emojis["red x"])
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
    async def end(self, ctx):
        log_command(ctx)
        if self.is_admin(ctx):
            pass

    @commands.command()
    async def playerlist(self, ctx):
        log_command(ctx)
        if not self.whitelist(
            ctx,
            dm=[UserType.ANY],
            channel=[UserType.ADMIN, UserType.CAPTAIN],
            channel_names=GENERIC_DRAFT_CHANNEL_NAMES,
        ):
            return
        await ctx.send(embed=embed.playerlist(self.auction.players))

    @commands.command()
    async def captainlist(self, ctx):
        log_command(ctx)
        if not self.whitelist(
            ctx,
            dm=[UserType.ANY],
            channel=[UserType.ADMIN, UserType.CAPTAIN],
            channel_names=GENERIC_DRAFT_CHANNEL_NAMES,
        ):
            return
        await ctx.send(embed=embed.captainlist(self.auction.captains))

    @commands.command()
    async def playerinfo(self, ctx):
        log_command(ctx)
        if not self.whitelist(
            ctx,
            dm=[UserType.ANY],
            channel=[UserType.ADMIN, UserType.CAPTAIN],
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
            await ctx.message.add_reaction(self.emojis["check"])
        except AuctionValidationError as e:
            if e.client_message.type == ClientMessageType.CHANNEL_MESSAGE:
                await ctx.send(e.client_message.data)
                await ctx.message.add_reaction(self.emojis["red x"])

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
            await ctx.message.add_reaction(self.emojis["check"])
        except AuctionValidationError as e:
            if e.client_message.type == ClientMessageType.CHANNEL_MESSAGE:
                await ctx.send(e.client_message.data)
                await ctx.message.add_reaction(self.emojis["red x"])

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
        teams = self.auction.get_current_teams()
        for keys, values in teams.items():
            await ctx.send(embed = embed.display_team(keys, values))

# keep_alive()
if __name__ == "__main__":
    client.add_cog(AuctionBot(client))

    # BOT TOKEN
    client.run(os.getenv("DISCORD_AUTH_TOKEN"))

