import discord
from replit import db
from draft import Auction
from lot import INITIAL_BID_TIMER_DEFAULT

def playerlist(players, is_picked=False):
    players = [p for p in players if not p["is_picked"]]
    players = sorted(players, key=lambda x: x["mmr"], reverse=True)

    player_names = [p["name"] for p in players]
    player_mmr = [str(p["mmr"]) for p in players]
    player_names_string = "\n".join(player_names)
    player_mmr_string = "\n".join(player_mmr)

    embed = discord.Embed(
        title="Player-list: ",
        color=0x7289da,
        description="All remaining players in the draft pool.",
    )

    embed.add_field(name="Player:", value=player_names_string)
    embed.add_field(name="MMR:", value=player_mmr_string)
    return embed


def captainlist(captains):
    captains = sorted(captains, key=lambda x: x["dollars"], reverse=True)

    captain_names = [c["name"] for c in captains]
    captain_dollars = [str(c["dollars"]) for c in captains]
    captain_names_string = "\n".join(captain_names)
    captain_dollars_string = "\n".join(captain_dollars)

    embed = discord.Embed(
        title="Captain-list: ",
        color=0x7289da,
        description="Captains and their remaining bank.",
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
        player.get("hero_drafter", ""),
    ]
    ratings_string = "\n".join(ratings)
    
    embed = discord.Embed(title="Player Info: ", color=0x7289da)
    embed.add_field(name="Name: ", value=player["name"], inline=True)
    embed.add_field(name="MMR: ", value=player.get('mmr', ''), inline=True)
    if player.get('opendota'):
        embed.add_field(name="Opendota: ", value=player.get('opendota', ''), inline=False)
    embed.add_field(name="Dotabuff: ", value=player["dotabuff"], inline=False)
    embed.add_field(name="Preferences: ", value=pref_string, inline=True)
    embed.add_field(name="(1-5) ", value=ratings_string, inline=True)
    if player.get('statement'):
        embed.add_field(name="Statement: ", value=player["statement"], inline=False)
    return embed
    

def winning_bid(nomination):
    if nomination.player_name == 'tornadospeed':
        embed = discord.Embed(
            title= 'Bidding Over!',
            color=0xc27c0e,
            description=f"{nomination.captain} has won the bidding on the cheater {nomination.player_name} for ${nomination.amount_paid}!",
        )
    else:
        embed = discord.Embed(
            title= 'Bidding Over!',
            color=0xc27c0e,
            description=f"{nomination.captain} has won the bidding on {nomination.player_name} for ${nomination.amount_paid}!",
        )
    return embed


def display_transition_to_nomination(captain, timer):
    embed = discord.Embed(
        title="Starting Nomination!",
        color=0xe91e63,
        description=f"{captain} is the next captain to nominate. You have {timer} seconds before the auto-nominator nominates for you.",
    )
    return embed


def display_successful_nomination(player, captain, timer):
    if player['name'] == 'tornadospeed':
        embed = discord.Embed(
            title=f"Nomination of notorious cheater {player['name']} by {captain['name']} successful!",
            color=0xe91e63,
            description=f'Bidding starts in {timer} seconds, {INITIAL_BID_TIMER_DEFAULT} seconds for the first bid.',
        )
    else:
        embed = discord.Embed(
            title=f"Nomination of {player['name']} by {captain['name']} successful!",
            color=0xe91e63,
            description=f'Bidding starts in {timer} seconds, {INITIAL_BID_TIMER_DEFAULT} seconds for the first bid.',
        )
    return embed


def display_team(captain, bank, players):
    names = '\n'.join([player.player_name for player in players])
    amounts = '\n'.join([str(player.amount_paid) for player in players])
    mmr = '\n'.join([str(player.player_mmr) for player in players])

    embed = discord.Embed(
        title=f'{captain}: ${bank}',
        color=0x2ecc71,
        description=f'',
    )

    embed.add_field(name='Name', value=names, inline = True)
    embed.add_field(name='MMR', value=mmr, inline = True)
    embed.add_field(name='Amount', value=amounts, inline = True)
    return embed

def display_break(timer):
    embed = discord.Embed(
        title='BREAK BETWEEN ROUNDS',
        color=0xe91e63,
        description=f'The draft will resume in {timer} seconds.',
    )
    return embed