import discord
from replit import db
from draft import Auction

def playerlist(players, is_picked=False):
    players = [p for p in players if not p["is_picked"]]
    players = sorted(players, key=lambda x: x["mmr"], reverse=True)

    player_names = [p["name"] for p in players]
    player_mmr = [str("{:.2f}".format(p["mmr"])) for p in players]
    player_names_string = "\n".join(player_names)
    player_mmr_string = "\n".join(player_mmr)

    embed = discord.Embed(
        title="Playerlist: ",
        color=0x1ABC9C,
        description="All remaining players in the draft pool.",
    )

    embed.add_field(name="Player:", value=player_names_string)
    embed.add_field(name="Draft Value:", value=player_mmr_string)
    return embed


def captainlist(captains):
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


def player_info(player):
    preferences = [
        "Pos 1: ",
        "Pos 2: ",
        "Pos 3: ",
        "Pos 4: ",
        "Pos 5: ",
        "Hero Drafter: ",
    ]
    pref_string = "\n".join(preferences)

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


def winning_bid(lot):
    embed = discord.Embed(
        title="We have a winner!",
        color=0x1ABC9C,
        description="The winning bid is:",
    )
    embed.add_field(name="Winner: ", value=lot.winning_bid["captain_name"])
    embed.add_field(name="Amount: ", value=lot.winning_bid["bid_amount"])
    embed.add_field(name="Player: ", value=lot.player)
    return embed


def display_transition_to_nomination(lot):
    embed_end_bidding = discord.Embed(
        title="Bidding has ended!",
        color=0x1ABC9C,
    )
    embed_end_nomination = discord.Embed(
        title="Nomination phase ",
        color=0x1ABC9C,
        description="It is " + lot.nominator + "'s turn to nominate a player.",
    )
    return embed_end_bidding, embed_end_nomination


def display_successful_nomination(lot, player):
    embed = discord.Embed(
        title="Nomination: ",
        color=0x1ABC9C,
        description="Nomination successful!",
    )
    embed.add_field(name="Player: ", value=player.name)
    embed.add_field(name="MMR: ", value=player.mmr)
    embed.add_field(name="Statement: ", value=player.statement)
    embed.add_field(name="Nominated by: ", value=lot.nominator)
    return embed


def display_team(team):
    embed = discord.Embed(
        title=f'Team {team[0].player_name}',
        color=0x1ABC9C,
        description='',
    )
    embed.add_field(name=team[1].player_name, value=team[1].amount_paid, inline = False)
    embed.add_field(name=team[2].player_name, value=team[2].amount_paid, inline = False)
    embed.add_field(name=team[3].player_name, value=team[3].amount_paid, inline = False)
    embed.add_field(name=team[4].player_name, value=team[4].amount_paid, inline = False)
    return embed