import asyncio
import os

from dotenv import load_dotenv
# This has to come first because it patches the env, and the replit-db looks for REPLIT_DB_URL in the env
load_dotenv()
from discord.ext import commands
from replit import db
from transitions import Machine

from draft import Auction, AuctionValidationError, ClientMessageType
import embed
import playerlist_util
from lot import Lot
from keep_alive import keep_alive

client = commands.Bot(command_prefix = '$')

@client.event
async def on_ready():
  print('Bot is ready.')


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
        await self.ctx.send(f'{self.captain_name} has {i} seconds left to nominate a player.')
      if i == 5:
        await self.ctx.send(f'{self.captain_name} has {i} seconds left to nominate a player.')

  def cancel(self):
    self.cancelled = True

CAPTAIN_NOMINATION_TIMEOUT = 30


class AuctionBot(commands.Cog): 
  def __init__(self, client, debug=False):
    self.start = 10                       #enter start timer
    self.nom = 30                         #enter nominating timer
    self.bid = 60                         #enter bidding timer
    self.admins = [
      411342580887060480,  # toth
      181700384279101440,  # fspoon
    ]
    self.league = 'PST'                   #enter league name

    self.client = client
    self.current_timer = None
    self.debug = debug
    self.current_lot = None
    self.auction = Auction()
  
    self.states = [
        'asleep',
        'starting', 
        'nominating', 
        'bidding', 
        'pausing', 
        'ending',
    ]
    self.machine = Machine(states=self.states, initial='asleep')
    self.machine.add_transition('start_machine', 'asleep', 'starting')
    self.machine.add_transition('nom_from_start', 'starting', 'nominating')
    self.machine.add_transition('bid_from_nom', 'nominating', 'bidding')
    self.machine.add_transition('nom_from_bid', 'bidding', 'nominating')
    self.machine.add_transition('end_from_bid', 'bidding', 'ending')

    # self.machine.add_transition('pause_from_start', 'starting', 'pausing')
    # self.machine.add_transition('pause_from_nom', 'nominating', 'pausing')
    # self.machine.add_transition('pause_from_bid', 'bidding', 'pausing')
    # self.machine.add_transition('pause_from_end', 'ending', 'pausing')

    # self.machine.add_transition('pause_to_start', 'pausing', 'starting')
    # self.machine.add_transition('pause_to_nom', 'pausing', 'nominating')
    # self.machine.add_transition('pause_to_bid', 'pausing', 'bidding')
    # self.machine.add_transition('pause_to_end', 'pausing', 'ending')
    self.playerCount = 0

    self.captains = []
    self.teams = []
    self.players = []
    self.bids = []

  def populate_from_db(self):
    if 'captains' in db.keys(): 
      self.captains = db['captains']
    if 'teams' in db.keys():
      self.teams = db['teams']
    if 'players' in db.keys():
      self.players = db['players']
    if 'bids' in db.keys():
      self.bids = db['bids']

  def delete_db(self):
    self.captains = db['captains']
    self.players = db['players']
    self.bids = db['bids']
    self.teams = db['teams']
    if not self.captains: 
      del db['captains']
    if not self.players:
      del db['players']
    if not self.bids:
      del db['bids']
    if not self.teams:
      del db['teams']
 
  def addCaptain(self, name, dollars):
    if self.checkCaptain(name):
      return False
    captain = {'name': name, 'dollars': dollars}
    self.captains.append(captain)
    db['captains'] = self.captains
    return True

  def removeCaptain(self, name):
    if self.checkCaptain(name):
      self.captains.remove(name)
      db['captains'] = self.captains
      return True
    return False
  
  def checkCaptain(self, name):
    for captain in self.captains:
      if captain['name'] == name:
        return True
    return False
  
  def rotateCaptainList(self):
    self.captains = db['captains']
    cap = self.captains[0]
    self.captains.append(cap)
    self.captains.pop(0)
    db['captains'] = self.captains

  def clearCaptains(self):
    self.captains.clear()
    db['captains'] = self.captains

  def addPlayer(self, name, mmr):
    if self.checkPlayer(name):
      return False
    player = {'name': name, 'mmr': mmr}
    self.players.append(player)
    db['players'] = self.players
    return True

  def removePlayer(self, name):
    if self.checkPlayer(name):
      self.players.remove()
      db['players'] = self.players
      return True
    return False

  def checkPlayer(self, name):
    for player in self.players:
      if player['name'] == name:
        return True
    return False
  
  def clearPlayers(self):
    self.players.clear()
    db['players'] = self.players

  def is_admin(self, ctx):
    if ctx.message.author.id in self.admins or self.debug:
      return True
    return False

  @commands.command()
  async def start(self, ctx):
    try:
      self.auction.start(ctx.message)
      await ctx.send(f'Welcome to the {self.league} Blind Vickrey Auction Draft!!')
      await ctx.send(f'The draft will begin in {self.start} seconds.')
      await ctx.send('Draft starting.')
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
    if self.machine.state == 'starting':
      self.machine.nom_from_start()
        
    elif self.machine.state == 'bidding':
      return
    
    elif self.machine.state == 'nominating':
      pass

    try: 
      new_lot = await self._nominate(ctx)
      if new_lot is None:
        await ctx.send("Invalid nomination, starting auto-nom timer")
        if self.current_timer is None:
          next_elibible_captain = self.auction.get_next_captain()
          self.current_timer = NominationTimer(CAPTAIN_NOMINATION_TIMEOUT, next_elibible_captain['name'], ctx)
          await self.current_timer.run()
          self.current_timer = None
          new_lot = self.auction.autonominate(next_elibible_captain)
          await ctx.send(f"Timer expired. Auto-nominator has nominated {new_lot.player} on behalf of {new_lot.nominator}")

      # We have a nomination, run the lot
      print(f"Starting lot {self.auction.current_lot.to_dict()}")
      for time_remaining in self.auction.run_current_lot():
        await asyncio.sleep(1)
        if time_remaining > 0 and time_remaining % 10 == 0:
          await ctx.send(f'{time_remaining} seconds left for player {self.auction.current_lot.player}')
      winning_bid = self.auction.current_lot.winning_bid
      await ctx.send(str(winning_bid))
      self.auction.give_lot_to_winner()

    except asyncio.CancelledError:
      print("Nomination timer cancelled successfully")
      pass

      
  @commands.command()
  async def bid(self, ctx):
    try:
      client_message = self.auction.bid(ctx.message)
      # TODO: React with client message
    except AuctionValidationError as e:
      if e.client_message.type == ClientMessageType.CHANNEL_MESSAGE:
        await ctx.send(e.client_message.data)
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
    await ctx.send(embed = embed.playerlist())
  
  @commands.command()
  async def captainlist(self, ctx):
    await ctx.send(embed = embed.captainlist())

  @commands.command()
  async def player(self, ctx):
    if self.is_admin(ctx):
      userInput = str(ctx.message.content)
      trash, name, mmr = userInput.rsplit(' ', 2)
      flag = self.addPlayer(name, mmr)
      if flag == True:
        await ctx.send('Player added.')
      else:
        await ctx.send('Player already added.')
    else:
      ctx.send('You are not authorized.')

  @commands.command()
  async def captain(self, ctx):
    if self.is_admin(ctx):
      name = ctx.message.mentions[0].name
      userInput = str(ctx.message.content)
      trash, trash, dollars = userInput.rsplit(' ', 2)
      flag = self.addCaptain(name, dollars)
      if flag == True:
        await ctx.send('Captain added.')
      else:
        await ctx.send('Captain already added.')
    else:
      ctx.send('You are not authorized.')

  @commands.command()
  async def upload_test_lists(self, ctx):
    playerlist = playerlist_util.parse_playerlist_csv('test_playerlist.csv')
    captainlist = playerlist_util.parse_captainlist_csv('test_captainlist.csv')
    await ctx.send('Starting test upload')

    for captain in captainlist:
      self.addCaptain(captain['name'], captain['captain_bank'])

    await ctx.send('Uploaded test captains')

    for player in playerlist:
      self.addPlayer(player['name'], player['draft_value'])

    await ctx.send('Uploaded test players')

  @commands.command()
  async def reset_captains_list_order(self, ctx):
    if not self.is_admin(ctx):
      return
    captains = db['captains']
    sorted_captains = sorted(captains, key=lambda x: x['dollars'], reverse=True)
    self.captains = sorted_captains
    db['captains'] = sorted_captains

  @commands.command()
  async def DELETE(self, ctx):
    if self.is_admin(ctx):
      await ctx.send('Are you sure you want to delete the database? y or n.')
      def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel and msg.content.lower() in ["y", "n"]
      msg = await client.wait_for("message", check=check)
      if msg.content.lower() == 'y':
        self.delete_db()
        print('test')
        await ctx.send('Databases Deleted. Restarting Bot.')
        await ctx.bot.logout()
        await ctx.login(os.getenv('DISCORD_AUTH_TOKEN'), bot=True)
      elif msg.content.lower() == 'n':
        await ctx.send('Databases not deleted.')
      else:
        pass
    else:
      pass

#keep_alive()
if __name__ == '__main__':
  client.add_cog(AuctionBot(client, debug=True))
  
  #BOT TOKEN
  print(os.getenv('DISCORD_AUTH_TOKEN'))
  client.run(os.getenv('DISCORD_AUTH_TOKEN'))