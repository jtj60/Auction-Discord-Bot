from discord.ext import commands
from replit import db
from transitions import Machine
from keep_alive import keep_alive
from timer import timer
import draft
import discord
import asyncio

client = commands.Bot(command_prefix = '$')

@client.event
async def on_command_error(ctx, error):
  if isinstance(error, commands.MissingRequiredArgument):
    await ctx.send('Wrong input, try again.')

@client.event
async def on_ready(ctx):
  await ctx.send('Im ready!')

class AuctionBot(commands.Cog): 
  def __init__(self, client):
    self.start = 10                       #enter start timer
    self.nom = 30                         #enter nominating timer
    self.bid = 60                         #enter bidding timer
    self.admin = 411342580887060480       #enter admin discord ID
    self.league = 'PST'                   #enter league name

    self.client = client
    self.current_timer = None
  
    self.states = [
        'asleep',
        'starting', 
        'nominating', 
        'bidding', 
        'pausing', 
        'ending',
    ]
    self.machine = Machine(model=self, states=self.states, initial='asleep')
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
    self.orders = []

  def populate_db(self):
    if 'captains' in db.keys(): 
      self.captains = db['captains']
    if 'teams' in db.keys():
      self.teams = db['teams']
    if 'players' in db.keys():
      self.players = db['players']
    if 'bids' in db.keys():
      self.bids = db['bids']
    if 'order' in db.keys():
      self.order = db['order']

  def delete_db():
    del db['captains']
    del db['bids']
    del db['players']
    del db['teams']
    del db['order']

  commands.command()
  async def hello(self, ctx):
    await ctx.send('pog')

  def addCaptain(self, name, dollars):
    for captain in self.captains:
      if self.checkCaptain():
        return False
    captain = {'name': name, 'dollars': dollars}
    self.captains.append(captain)
    self.populate_db()
    return True

  def removeCaptain(self, name):
    for captain in self.captains:
      if self.checkCaptain():
        self.captains.remove(captain)
        self.populate_db()
        return True
    return False
  
  def checkCaptain(self, name):
    for captain in self.captains:
      if captain['name'] == name:
        return True
    return False

  def clearCaptains(self):
    self.captains.clear()
    self.populate_db()

  def addPlayer(self, name, mmr):
    for player in self.players:
      if self.checkPlayer():
        return False
    player = {'name': name, 'mmr': mmr}
    self.players.append(player)
    self.populate_db()
    return True

  def removePlayer(self, name):
    for player in self.players:
      if self.checkPlayer():
        self.players.remove(player)
        self.populate_db()
        return True
    return False

  def checkPlayer(self, name):
    for player in self.players:
      if player['name'] == name:
        return True
    return False
  
  def clearPlayers(self):
    self.players.clear()
    self.populate_db()

  def addBid(self, name, amount):
    for bid in self.bids:
      if self.checkBid():
        return False
    bid = {'name': name, 'amount': amount}
    self.bids.append(bid)
    self.populate_db()
    return True

  def removeBid(self, name):
    for bid in self.bids:
      if self.checkBid():
        self.bids.remove(bid)
        self.populate_db()
        return True
    return False

  def checkBid(self, name):
    for bid in self.bids:
      if bid['name'] == name:
        return True
    return False

  def clearBids(self):
    self.bids.clear()
    self.populate_db()

  def makeOrder(self):
    for captain in self.order:
      self.order.append(self.captains[captain])
      self.order = sorted(self.order, key = lambda x: x['dollars'], reverse = False)
      self.populate_db()
  
  def checkOrder(self, name):
    for captain in self.order:
      if self.order['name'] == name:
        return True
    return False
  
  def updateOrder(self):
    for captain in self.order:
      if self.checkOrder():
        self.order.remove(captain)
        self.order.append(captain)
        self.populate_db()
        return True
    return False
    
  async def timer(t):
    for i in range(t, 0, -1):
      await asyncio.sleep(1)
      #do countdown logic
      while i >= 20:
        await asyncio.sleep(10)
        yield i
      if i <= 5:
        yield i

  commands.command()
  async def start(self, ctx):
    if ctx.message.author == self.admin:
      self.state_machine.start_machine()
      await ctx.send(f'Welcome to the {self.league} Blind Vickrey Auction Draft!!')
      await ctx.send(f'The draft will begin in {self.start} seconds.')
      async for sec in timer(self.start): 
        await ctx.send(sec)
      await ctx.send('Draft starting.')
      self.playerCount = draft.playerCount()

  async def checkNom(self, ctx, nom_timer):
    if ctx.message.author == self.order['name']: 
      if self.checkPlayer(ctx.message):
        await ctx.send(f'{ctx.message} nominated.')
        nom_timer.cancel()
        return True
      else:
        await ctx.send(f'{ctx.message} does not exist')
    return False
        
  commands.command()
  async def nominate(self, ctx):
    if self.machine.state == 'starting':
      self.machine.nom_from_start()
      self.current_timer = asyncio.create_task(self.timer(self.nom))
      try: 
        self.checkNom(ctx, self.timer)
        await self.timer
      except asyncio.CancelledError:
        pass
        #discord output
      finally: 
        if not self.timer.cancelled():
          #player auto-nominated
          #change state
          #discord output
          pass
        else: 
          #change state
          pass
        
    elif self.machine.state == 'bidding':
      pass
    
    elif self.machine.state == 'nominating':
      try: 
        self.checkNom(ctx, self.timer)
        await self.timer
      except asyncio.CancelledError:
        #player nominated
        #discord output
        pass
      finally: 
        if not self.timer.cancelled():
          #player auto-nominated
          #change state
          #discord output
          pass
        else: 
          #change state
          pass
      pass
      
  commands.command()
  async def bid(self, ctx):
    if self.machine.state == 'bidding':
      self.current_timer = asyncio.create_task(self.timer(self.nom))
      try:
        pass
      except:
        pass
      
    elif self.machine == 'nominating':
      pass

    else:
      pass
  
  commands.command()
  async def pause(self, ctx):
    pass
  
  commands.command()
  async def end(self, ctx):
    pass

  commands.command()
  def runDraft(self):
    self.start()
    
    while self.playerCount != 0:
      self.nominate()
      self.bid()
      self.playerCount = draft.playerCount()
    
    self.end()
  


#keep_alive()

client.add_cog(AuctionBot(client))
#BOT TOKEN
client.run('')

#def setup(bot):
 #  bot.add_cog(AuctionBot(bot))
