from replit import db as replit_db

from transitions import Machine

from collections import namedtuple
from lot import Lot

class ClientMessageType:
  CHANNEL_MESSAGE = 0
  REACT = 1
  DIRECT_MESSAGE = 2

ClientMessage = namedtuple('ClientMessage', ['type', 'data'])

class AuctionValidationError(Exception):
  def __init__(self, client_message):
    super().__init__()
    self.client_message = client_message

class Auction:
  def __init__(self, db=None):
    if db is not None:
      self.db = db
    else:
      self.db = replit_db

    self.admins = [
      411342580887060480,  # toth
      181700384279101440,  # fspoon
    ]
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

    self.captains = []
    self.teams = []
    self.players = []
    self.bids = []

    self.current_lot = None

  def populate_from_db(self):
    if 'captains' in self.db.keys(): 
      self.captains = self.db['captains']
    if 'teams' in self.db.keys():
      self.teams = self.db['teams']
    if 'players' in self.db.keys():
      self.players = self.db['players']
    if 'bids' in self.db.keys():
      self.bids = self.db['bids']

  def delete_db(self):
    for key in ['captains', 'players', 'bids', 'teams']:
      try:
        setattr(self, key, [])
        del self.db[key]
      except KeyError:
        pass

  def addCaptain(self, name, dollars):
    if self.checkCaptain(name):
      return False
    captain = {'name': name, 'dollars': dollars}
    self.captains.append(captain)
    self.db['captains'] = self.captains
    return True

  def checkCaptain(self, name):
    for captain in self.captains:
      if captain['name'] == name:
        return True
    return False

  def rotateCaptainList(self):
    self.captains = self.db['captains']
    cap = self.captains[0]
    self.captains.append(cap)
    self.captains.pop(0)
    self.db['captains'] = self.captains

  def clearCaptains(self):
    self.captains = []
    self.db['captains'] = self.captains

  def addPlayer(self, name, mmr):
    if self.checkPlayer(name):
      return False
    player = {'name': name, 'mmr': mmr}
    self.players.append(player)
    self.db['players'] = self.players
    return True

  def removePlayer(self, name):
    # TODO: This function clearly does not work
    if self.checkPlayer(name):
      self.players.remove()
      self.db['players'] = self.players
      return True
    return False

  def checkPlayer(self, name):
    for player in self.players:
      if player['name'] == name:
        return True
    return False
  
  def clearPlayers(self):
    self.players = []
    self.db['players'] = self.players

  def is_admin(self, message):
    if message.author.id in self.admins or self.debug:
      return True
    return False

  def get_next_captain(self):
    return self.db['captains'][0]

  def start(self, message):
    if self.is_admin(message):
      self.populate_from_db()
      self.machine.start_machine()
    else:
      raise AuctionValidationError(ClientMessage(
        ClientMessageType.CHANNEL_MESSAGE, 
        'You are not an admin.',
      ))

  def autonominate(self, next_eligible_captain):
    players_by_mmr = sorted(self.db['players'], key=lambda x: x['mmr'], reverse=True)
    player_to_autonominate = players_by_mmr[0]
    self.current_lot = Lot(player_to_autonominate['name'], next_eligible_captain['name'])
    return self.current_lot

  def _validate_captain(self, message):
    message_parts = message.content.split()
    captain_name = message.author.name
    if len(message_parts) > 2:
      captain_name = message_parts[2]
      if not self.is_admin(message):
        print(f"Couldn't admin override {captain_name}, not admin")
        return None
      if not self.checkCaptain(captain_name):
        print(f"Couldn't admin override {captain_name}, not a captain")
        return None
    return [captain for captain in self.db['captains'] if captain['name'] == captain_name][0]

  def _validate_bid_amount(self, message, captain):
    message_parts = message.content.split()
    if len(message_parts) < 2:
      return None
    try:
      bid_amount = int(message_parts[1])
    except ValueError:
      return None
    if bid_amount < 0:
      return None

    if bid_amount > captain['dollars']:
      raise AuctionValidationError(ClientMessage(
        ClientMessageType.CHANNEL_MESSAGE, 
        f"{captain['name']} doesn't have enough money to bid {bid_amount}.",
      ))
    return bid_amount

  def bid(self, message):
    if self.machine.state != 'bidding':
      print(f"Received bid in state {self.machine.state}, ignoring")
      return
    captain = self._validate_captain(message)
    bid_amount = self._validate_bid_amount(message, captain)
    if bid_amount is None:
      raise AuctionValidationError(ClientMessage(
        ClientMessageType.REACT, 
        "-",
      ))
      return
    if not self.current_lot:
      print("This shouldn't happen, in bidding state but no current lot")
    self.current_lot.add_bid(dict(captain_name=captain['name'], amount=bid_amount))
    return ClientMessage(
      ClientMessageType.REACT,
      "+"
    )

  def nominate(self, message):
    message_parts = message.content.split()
    nominated_player_name = message_parts[1]
    # TODO: Make sure this author was allowed to nominate
    nominated_on_behalf_of_captain = message.author.name
    if not self.checkPlayer(nominated_player_name):
      raise AuctionValidationError(ClientMessage(
        type=ClientMessageType.CHANNEL_MESSAGE,
        data='That player is not in the system.'
      ))

    if len(message_parts) > 2:
      nominated_on_behalf_of_captain = message_parts[2]
      if not self.is_admin(message):
        raise AuctionValidationError(ClientMessage(
          type=ClientMessageType.CHANNEL_MESSAGE,
          data=f"Can't nominate {nominated_player_name} on behalf of {nominated_on_behalf_of_captain}, not admin",
        ))
      if not self.checkCaptain(nominated_on_behalf_of_captain):
        raise AuctionValidationError(ClientMessage(
          type=ClientMessageType.CHANNEL_MESSAGE,
          data=f"Can't nominate {nominated_player_name} on behalf of {nominated_on_behalf_of_captain}, not a captain",
        ))
    else:
      next_eligible_captain = self.get_next_captain()
      if nominated_on_behalf_of_captain != next_eligible_captain['name']:
        data = f'{nominated_on_behalf_of_captain} is not eligible to nominate at this time'
        raise AuctionValidationError(ClientMessage(
          type=ClientMessageType.CHANNEL_MESSAGE,
          data=data,
        ))

    if self.machine.state == 'starting':
      self.machine.nom_from_start()

    self.current_lot = Lot(nominated_player_name, nominated_on_behalf_of_captain)
    return self.current_lot

  def clear_lot(self):
    self.current_lot = None

  def give_lot_to_winner(self):
    pass

  def run_current_lot(self):
    self.machine.bid_from_nom()
    for time_remaining in self.current_lot.run_lot():
      yield time_remaining
    
    self.rotateCaptainList()
    self.machine.nom_from_bid()