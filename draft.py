from replit import db

def nominate():
  return

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

