from transitions import Machine
import discord

class AuctionMachine(object):
  
  # Blind Auction states
  states = ['asleep','starting', 'nominating', 'bidding', 'pausing', 'ending']

  def _init_(self, name):
    
    self.name = name
    self.players_bid_upon = 0

    # Initializing the state machine
    self.machine = Machine(model = self, states = AuctionMachine.states, initial = 'asleep')

    # Adding transistions: self.machine.add_transition(trigger = '', source = '', destination = '')
    # Non-pause transitions
    self.machine.add_transition('start_machine', 'asleep', 'starting')
    self.machine.add_transition('nom_from_start', 'starting', 'nominating')
    self.machine.add_transition('bid_from_nom', 'nominating', 'bidding')
    self.machine.add_transition('nom_from_bid', 'bidding', 'nominating')
    self.machine.add_transition('end_from_bid', 'bidding', 'ending')

    # Pause transitions
    self.machine.add_transition('pause_from_start', 'starting', 'pausing')
    self.machine.add_transition('pause_from_nom', 'nominating', 'pausing')
    self.machine.add_transition('pause_from_bid', 'bidding', 'pausing')
    self.machine.add_transition('pause_from_end', 'ending', 'pausing')
    
    # Unpause transitions
    self.machine.add_transition('unpause_to_start', 'pausing', 'starting')
    self.machine.add_transition('unpause_to_nom', 'pausing', 'nominating')
    self.machine.add_transition('unpause_to_bid', 'pausing', 'bidding')
    self.machine.add_transition('unpause_to_end', 'pausing', 'ending')

  ## wait X amount of time for a bid to come up, trigger state when event occurs
  def listen_for_bid(): 
    pass
  def process_bid(): 
    pass

#start

def start_machine(): 
  if message.content.startswith('#start'):
    if message.author.id == admin:
      auction = AuctionMachine('Auction')
      auction.start_machine()
      
      await message.channel.send ('Welcome to the PST Season 25 Draft!')
      await message.channel.send ('Draft will begin in 10 seconds.')
      async for sec in timer(1): 
        await message.channel.send(sec)
      await message.channel.send('Draft Starting!')

  #Start the machine
  machine.start_machine()