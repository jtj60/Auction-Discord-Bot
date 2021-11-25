from discord.ext import commands
from replit import db
from transitions import Machine
from keep_alive import keep_alive
import draft
import embed
import asyncio
import playerlist_util
from lot import Lot

client = commands.Bot(command_prefix = '$')

@client.event
async def on_ready():
  print('Bot is ready.')



async def timer(t):
  for i in range(t, 0, -1):
    await asyncio.sleep(1)
    #do countdown logic
    while i >= 20 and i % 20 == 0:
      yield i
    if i <= 5:
      yield i

async def coroutine_wrapper(async_gen, args):
  try:
    print(tuple([i async for i in async_gen(args)]))
  except ValueError:
    print(tuple([(i, j) async for i, j in async_gen(args)]))

CAPTAIN_NOMINATE_TIMEOUT = 30



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

  def addBid(self, name, amount):
    for bid in self.bids:
      if self.checkBid():
        return False
    bid = {'name': name, 'amount': amount}
    self.bids.append(bid)
    db['bids'] = self.bids
    return True

  def removeBid(self, name):
    for bid in self.bids:
      if self.checkBid():
        self.bids.remove(bid)
        db['bids'] = self.bids
        return True
    return False

  def checkBid(self, name):
    for bid in self.bids:
      if bid['name'] == name:
        return True
    return False

  def clearBids(self):
    self.bids.clear()
    db['bids'] = self.bids

  def is_admin(self, ctx):
    if ctx.message.author.id in self.admins or self.debug:
      return True
    return False


  @commands.command()
  async def start(self, ctx):
    if self.is_admin(ctx):
      self.populate_from_db()
      self.machine.start_machine()
      await ctx.send(f'Welcome to the {self.league} Blind Vickrey Auction Draft!!')
      await ctx.send(f'The draft will begin in {self.start} seconds.')
      # async for sec in timer(self.start): 
      #   await ctx.send(sec)
      await ctx.send('Draft starting.')
      #self.playerCount = draft.playerCount()
    else:
      await ctx.send('UNAUTHORIZED ACCESS')

  async def checkNom(self, ctx, nom_timer):
    self.captains = db['captains']
    cap = self.captains[0]
    if ctx.message.author.name == cap['name']:
      if self.checkPlayer(ctx.message):
        await ctx.send(f'{ctx.message} nominated.')
        nom_timer.cancel()
        return True
      else:
        await ctx.send(f'{ctx.message} does not exist')
    return False

  async def get_next_captain(self):
    return db['captains'][0]

  async def _nominate(self, ctx):
    message_parts = ctx.message.content.split()
    if not message_parts:
      return None

    nominated_player_name = message_parts[1]
    # TODO: Make sure this author was allowed to nominate
    nominated_on_behalf_of_captain = ctx.message.author.name
    if not self.checkPlayer(nominated_player_name):
      await ctx.send(f"Can't nominate {nominated_player_name}, they don't exist in db")
      return None

    if len(message_parts) > 2:
      nominated_on_behalf_of_captain = message_parts[2]
      if not self.is_admin(ctx):
        await ctx.send(f"Can't nominate {nominated_player_name} on behalf of {nominated_on_behalf_of_captain}, not admin")
      if not self.checkCaptain(nominated_on_behalf_of_captain):
        await ctx.send(f"Can't nominate {nominated_player_name} on behalf of {nominated_on_behalf_of_captain}, not a captain")
    else:
      next_eligible_captain = await self.get_next_captain()
      if nominated_on_behalf_of_captain != next_eligible_captain['name']:
        ctx.send(f'{nominated_on_behalf_of_captain} is not eligible to nominate at this time')

    # Someone was waiting on a successful nomination, let them know it's done
    if self.current_timer is not None:
      self.current_timer.cancel()
      self.current_timer = None

    self.current_lot = Lot(nominated_player_name, nominated_on_behalf_of_captain)
    return self.current_lot

  async def _autonominate(self, ctx):
    players_by_mmr = sorted(db['players'], key=lambda x: x['mmr'], reverse=True)
    player_to_autonominate = players_by_mmr[0]
    next_eligible_captain = await self.get_next_captain()
    self.current_lot = Lot(player_to_nominate['name'], next_eligible_captain['name'])
    return self.current_lot
    
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
          self.current_timer = asyncio.create_task(coroutine_wrapper(timer(CAPTAIN_NOMINATE_TIMEOUT)))
          await self.current_timer
          new_lot = await self._autonominate(ctx) 
          await ctx.send(f"Timer expired. Auto-nominator has nominated {new_lot.player} on behalf of {new_lot.nominator}")
      else:
        self.machine.bid_from_nom()
      async for time_remaining in self.current_lot.run_lot(initial_timer=60):
        if time_remaining > 0 and time_remaining % 10 == 0:
          await ctx.send(f'{time_remaining} seconds left for player {self.current_lot.player}')
      winning_bid = self.current_lot.winning_bid
      await ctx.send(str(winning_bid))
      self.rotateCaptainList()
      self.machine.nom_from_bid()
    except asyncio.CancelledError:
      pass
      
  @commands.command()
  async def bid(self, ctx):
    if self.machine.state == 'bidding':
      self.current_timer = asyncio.create_task(self.timer(self.nom))
      try:
        self.checkNom(ctx, self.timer)
        await self.timer
      except :
        pass
      
    elif self.machine == 'nominating':
      pass

    else:
      pass
  
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
        await ctx.login('OTAxMjQ0MzMxOTA0NjIyNTky.YXNDMQ.TQ3L0okK99Ka69VLkALuVCDX3Uo', bot=True)
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
  client.run('OTAxMjQ0MzMxOTA0NjIyNTky.YXNDMQ.TQ3L0okK99Ka69VLkALuVCDX3Uo')