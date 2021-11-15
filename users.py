from replit import db   

def addPlayer(name, mmr):
  from main import players
  for player in players:
    if player['name'] == name:
      return True
  player = {'name': name, 'mmr': mmr}
  players.append(player)
  db['players'] = players
  return False

def addCaptain(name, dollars):
  from main import captains
  for captain in captains:
    if captain['name'] == name:
      return True
  captain = {'name': name, 'dollars': dollars}
  captains.append(captain)
  db['captains'] = captains
  return False

def checkCaptain(name):
  captains = db['captains']
  for captain in captains:
    if captain['name'] == name:
      return True
  return False

def removePlayer(name):
  players = db['players']
  for player in players:
    if player['name'] == name:
      players.remove(player)
      db['players'] = players
      return True
  return False

def removeCaptain(name):
  captains = db['captains']
  for captain in captains:
    if captain['name'] == name:
      captains.remove(captain)
      db['captains'] = captains
      return True
  return False