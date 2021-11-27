import discord
from replit import db


def playerlist():
    players = db["players"]
    players = sorted(players, key=lambda x: x["mmr"], reverse=True)

    player_names = [p["name"] for p in players]
    player_mmr = [str(p["mmr"]) for p in players]
    player_names_string = "\n".join(player_names)
    player_mmr_string = "\n".join(player_mmr)

    embed = discord.Embed(
        title="Playerlist: ",
        color=0x1ABC9C,
        description="All remaining players in the draft pool.",
    )

    embed.add_field(name="Player:", value=player_names_string)
    embed.add_field(name="MMR:", value=player_mmr_string)
    return embed


def captainlist():
    captains = db["captains"]
    captains = sorted(captains, key=lambda x: x["dollars"], reverse=True)

    captain_names = [c["name"] for c in captains]
    captain_dollars = [str(c["dollars"]) for c in captains]
    captain_names_string = "\n".join(captain_names)
    captain_dollars_string = "\n".join(captain_dollars)

    embed = discord.Embed(
        title="Playerlist: ",
        color=0x1ABC9C,
        description="All remaining players in the draft pool.",
    )

    embed.add_field(name="Player:", value=captain_names_string)
    embed.add_field(name="Dollars:", value=captain_dollars_string)
    return embed


def player_info(message):
    players = db["players"]
    message_parts = message.content.split()
    preferences = [
        "Pos 1: ",
        "Pos 2: ",
        "Pos 3: ",
        "Pos 4: ",
        "Pos 5: ",
        "Hero Drafter: ",
    ]
    pref_string = "\n".join(preferences)
    name = message_parts[1]
    for player in players:
        if player["name"] == name:
            ratings = [
                player["pos1"],
                player["pos2"],
                player["pos3"],
                player["pos4"],
                player["pos5"],
                player["hero_drafter"],
            ]
            ratings_string = "\n".join(ratings)
            embed = discord.Embed(title="Player Info: ", color=0xE91E63)
            embed.add_field(name="Name: ", value=player["name"], inline=True)
            embed.add_field(name="Badge: ", value=player["badge"], inline=True)
            embed.add_field(name="Opendota: ", value=player["opendota"], inline=False)
            embed.add_field(name="Dotabuff: ", value=player["dotabuff"], inline=False)
            embed.add_field(name="Preferences: ", value=pref_string, inline=True)
            embed.add_field(name="(1-5) ", value=ratings_string, inline=True)
            embed.add_field(name="Statement: ", value=player["statement"], inline=False)
            return embed
