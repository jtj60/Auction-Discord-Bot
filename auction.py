import discord    
from replit import db  
from state_machine import AuctionMachine                         
from keep_alive import keep_alive           
from timer import timer 
import bid
import draft
import users
import embed

captains = []
if 'captains' in db.keys():
  captains = db['captains']

teams = []
if 'teams' in db.keys():
  teams = db['teams']

players = []
if 'players' in db.keys():
  players = db['players']

bids = []
if 'bids' in db.keys():
  bids = db['bids']



class AuctionBot(discord.Client): 
  def __init__(self, name):
    captains = []
    teams = []
    players = []
    bids = []
    self.populate_db()

  def populate_db():
    if 'captains' in db.keys(): 
      do stuff

    if 'teams' in db.keys():
      do more stuff

      etc'

  def add_captain():
    #to stuff
    populate_db()






#del db['captains']
#del db['bids']
#del db['players']
#del db['teams']


admin = 411342580887060480 #enter admin discord ID

client = discord.Client()

@client.event
async def on_ready():
  print('We have logged in as {0.user}'.format(client))

#To recieve messages from users. 
@client.event
async def on_message(message):
  
  if message.author == client.user:
    return

  if message.content.startswith('#ready'):
    await message.author.send('Submit bids here.')

  if message.content.startswith('#start'):
    if message.author.id == admin:
      auction = AuctionMachine('Auction')
      auction.start_machine()
      
      await message.channel.send ('Welcome to the PST Season 25 Draft!')
      await message.channel.send ('Draft will begin in 10 seconds.')
      async for sec in timer(1): 
        await message.channel.send(sec)
      await message.channel.send('Draft Starting!')

      count = draft.playerCount()
      while count != 0:
        auction.nom_from_start()
      
      
      
      
      
      
      # count = draft.playerCount()
      # while count != 0:
      #   await message.channel.send(f'It is PLACEHOLDER turn to nominate. You have 15 seconds')
        
      #   async for sec in timer(1): 
      #     await message.channel.send(sec)
      #     nominated = False
      #     if message.content.startswith('#nominate'):
      #       userInput = message.content
      #       trash, name = userInput.rsplit(' ')
      #       player = draft.getPlayer(name)
      #       nominated = True
          
      #     if sec == 1:
      #       if nominated == False:
      #         player = draft.nextPlayer()
      #         await message.channel.send(f'Failed to nominate. {player["name"]} nominated instead. Bidding begins now. You have 60 seconds.')
      #       else:
      #         await message.channel.send(f'{player["name"]} nominated. Bidding begins now. You have 60 seconds.')
        
      #   async for sec in timer(15): 
      #     await message.channel.send(sec)
          
      #     msg = await client.wait_for('message')
          
      #       print('test')
      #       username = msg.author.name
      #       amount = msg.content
      #       print(username)
      #       print(amount)
            
      #       captain = draft.getCaptain(username)
      #       if captain['dollars'] >= amount:
      #         bid.addBid(username, amount)
      #         await message.author.send('Bid submitted.')
      #       else:
      #         await message.author.send('Bid failed. Not enough money.')
          
      #     if sec == 1:
      #       await message.channel.send(f'Bidding closed for {player["name"]}.')
      #       highestBid = bid.bidder()
      #       cap = highestBid['name']
      #       cost = highestBid['amount']
      #       await message.channel.send(f'{cap} purchased {player["name"]} for ${cost}.')
      #       #update teams here
      #       users.removePlayer(player['name'])
      #       count = draft.playerCount()
  
  if message.content.startswith('#playerlist'):
    await message.channel.send(embed = embed.playerlist())
  
  if message.content.startswith('#captainlist'):
    await message.channel.send(embed = embed.captainlist())

  if message.content.startswith('#addPlayer'):
    userInput = message.content
    trash, name, mmr = userInput.rsplit(' ', 2)
      
    flag = users.addPlayer(name, mmr)
    if flag == False:
      await message.channel.send('Player added.')
    else:
      await message.channel.send('Player not added.')

  if message.content.startswith('#addCaptain'):
    name = message.mentions[0].name
    dollars = 1000
    flag = users.addCaptain(name, dollars)
    if flag == False:
      await message.channel.send('Captain added.')
    else:
      await message.channel.send('Captain not added.')
    
keep_alive()

#BOT TOKEN
client.run('OTAxMjQ0MzMxOTA0NjIyNTky.YXNDMQ.eYTemC4HYrttRp3I-luGroViwpg')
