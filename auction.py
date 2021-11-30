import asyncio
import os

from dotenv import load_dotenv

# This has to come first because it patches the env, and the replit-db looks for REPLIT_DB_URL in the env
load_dotenv()
from discord.ext import commands
from replit import db
from transitions import Machine

from draft import Auction, AuctionValidationError, ClientMessageType
from draft import ADMIN_IDS
import embed
import playerlist_util
from lot import Lot
from keep_alive import keep_alive

client = commands.Bot(command_prefix="$")


@client.event
async def on_ready():
    print("Bot is ready.")


class NominationTimer:
    def __init__(self, t, captain_name, ctx):
        self.t = t
        self.captain_name = captain_name
        self.ctx = ctx
        self.cancelled = False

    async def run(self):
        for i in range(self.t, 0, -1):
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

    def cancel(self):
        self.cancelled = True


CAPTAIN_NOMINATION_TIMEOUT = 30


class AuctionBot(commands.Cog):
    def __init__(self, client, debug=False):
        self.start = 10  # enter start timer
        self.nom = 30  # enter nominating timer
        self.bid = 60  # enter bidding timer
        self.admins = [
            411342580887060480,  # toth
            181700384279101440,  # fspoon
        ]
        self.league = "PST"  # enter league name
        self.emojis = {
            "plus": "<:plus:913878220489773099>",  # plus for bot reaction
            "minus": "<:minus:913877912355229727>",  # minus for bot reaction
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

    @commands.command()
    async def start(self, ctx):
        try:
            self.auction.start(ctx.message)
            await ctx.send(
                f"Welcome to the {self.league} Blind Vickrey Auction Draft!!"
            )
            await ctx.send(f"The draft will begin in {self.start} seconds.")
            await ctx.send("Draft starting.")
        except AuctionValidationError as e:
            if e.client_message.type == ClientMessageType.CHANNEL_MESSAGE:
                await ctx.send(e.client_message.data)

    async def _nominate(self, ctx):
        message_parts = ctx.message.content.split()
        if not message_parts:
            return None

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
        try:
            new_lot = await self._nominate(ctx)
            if new_lot is None:
                await ctx.send("Invalid nomination, starting auto-nom timer")
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
            print(f"Starting lot {self.auction.current_lot.to_dict()}")
            await ctx.send(embed=embed.player_info(ctx.message))
            for time_remaining in self.auction.run_current_lot():
                await asyncio.sleep(1)
                if time_remaining > 0 and time_remaining % 10 == 0:
                    await ctx.send(
                        f"{time_remaining} seconds left for player {self.auction.current_lot.player}"
                    )
            self.auction.give_lot_to_winner()

        except asyncio.CancelledError:
            print("Nomination timer cancelled successfully")
            pass

    @commands.command()
    async def bid(self, ctx):
        try:
            flag = self.auction.bid(ctx.message)
            if flag is not None:
                await ctx.message.add_reaction(self.emojis["plus"])
        except AuctionValidationError as e:
            if e.client_message.type == ClientMessageType.CHANNEL_MESSAGE:
                await ctx.send(e.client_message.data)
                await ctx.message.add_reaction(self.emojis["minus"])
            return None

    @commands.command()
    async def pause(self, ctx):
        if self.is_admin(ctx):
            pass

    @commands.command()
    async def end(self, ctx):
        if self.is_admin(ctx):
            pass

    @commands.command()
    async def playerlist(self, ctx):
        await ctx.send(embed=embed.playerlist())

    @commands.command()
    async def captainlist(self, ctx):
        await ctx.send(embed=embed.captainlist())

    @commands.command()
    async def playerinfo(self, ctx):
        await ctx.send(embed=embed.player_info(ctx.message))

    @commands.command()
    async def player(self, ctx):
        try:
            self.auction.player(ctx.message)
            await ctx.message.add_reaction(self.emojis["plus"])
        except AuctionValidationError as e:
            if e.client_message.type == ClientMessageType.CHANNEL_MESSAGE:
                await ctx.send(e.client_message.data)
                await ctx.message.add_reaction(self.emojis["minus"])

    @commands.command()
    async def captain(self, ctx):
        try:
            self.auction.captain(ctx.message)
            await ctx.message.add_reaction(self.emojis["plus"])
        except AuctionValidationError as e:
            if e.client_message.type == ClientMessageType.CHANNEL_MESSAGE:
                await ctx.send(e.client_message.data)
                await ctx.message.add_reaction(self.emojis["minus"])

    @commands.command()
    async def upload_test_lists(self, ctx):
        if not self.is_admin(ctx):
            return
        self.auction.bootstrap_from_testlists()
        await ctx.send("Test lists uploaded")

    @commands.command()
    async def DELETE(self, ctx):
        if not self.is_admin(ctx):
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


# keep_alive()
if __name__ == "__main__":
    client.add_cog(AuctionBot(client, debug=True))

    # BOT TOKEN
    client.run(os.getenv("DISCORD_AUTH_TOKEN"))