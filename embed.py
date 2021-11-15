import discord
from replit import db

def playerlist():
  players = db['players']
  players = sorted(players, key = lambda x: x['mmr'], reverse = True)
  
  player_names = [p['name'] for p in players]
  player_mmr = [str(p['mmr']) for p in players]
  player_names_string = '\n'.join(player_names)
  player_mmr_string = '\n'.join(player_mmr)
    
  embed = discord.Embed(title = 'Playerlist: ', color = 0x1abc9c, description= 'All remaining players in the draft pool.')
 
  embed.add_field(name = 'Player:', value = player_names_string)
  embed.add_field(name= 'MMR:', value = player_mmr_string)
  return embed

def captainlist():
  captains = db['captains']
  captains = sorted(captains, key = lambda x: x['dollars'], reverse = True)
  
  captain_names = [c['name'] for c in captains]
  captain_dollars = [str(c['dollars']) for c in captains]
  captain_names_string = '\n'.join(captain_names)
  captain_dollars_string = '\n'.join(captain_dollars)
    
  embed = discord.Embed(title = 'Playerlist: ', color = 0x1abc9c, description= 'All remaining players in the draft pool.')
 
  embed.add_field(name = 'Player:', value = captain_names_string)
  embed.add_field(name= 'Dollars:', value = captain_dollars_string)
  return embed

  