from replit import db

from transitions import Machine
class Auction:

  def __init__(self):
    pass


class Draft():

  def playerCount():
    players = db['players']
    playercount = len(players)
    return playercount

  def getPlayer(name):
    players = db['players']
    for player in players:
      if player['name'] == name:
        return player
      else:
        return 0

  def nextPlayer():
    players = db['players']
    players = sorted(players, key = lambda x: x['mmr'], reverse = True)
    return players[0]
  
  def getCaptain(name):
    captains = db['captains']
    for captain in captains:
      if captain['name'] == name:
        return captain
      else:
        return 0

  def bidCount(self):
    bidcount = len(self.bids)
    return bidcount

  def highestBid(self):
    return max(self.bids['amount'])

  # def bidder(self):
  #   count = self.bidCount()
  #   if count >= 2:
  #     highBid = self.highestBid()
  #     self.removeBid(highBid['name'])
  #     self.populate_db()
  #     nextBid = self.highestBid()
  #     self.clearBids()
  #     vickreyPrice = nextBid['amount']
  #     highBid['amount'] = vickreyPrice
  #   elif count == 1:
  #     highBid == self.highestBid()
  #     highBid['amount'] = 0
  #   captains = db['captains']
  #   for captain in captains:
  #     if captain['name'] == highBid['name']:
  #       captain['dollars'] = captain['dollars'] - highBid['amount']
  #       db['captains'] = captains 
  #   return highBid

