import csv
import fractions
import pprint


def parse_playerlist_csv(filename):
    with open(filename) as f:
        reader = csv.DictReader(f)

        players = []
        for row in reader:
            player = {}
            if not row["name"]:
                continue

            player["name"] = row["name"]
            player["draft_value"] = float(
                sum(fractions.Fraction(s) for s in row["Draft Value"].split())
            )
            player["badge"] = row["Medal"]
            player["opendota"] = row["opendota"]
            player["dotabuff"] = row["dotabuff"]
            player["statement"] = row["statement"]
            player["pos1"] = row["Pos 1"]
            player["pos2"] = row["Pos 2 "]
            player["pos3"] = row["Pos 3"]
            player["pos4"] = row["Pos 4"]
            player["pos5"] = row["Pos 5"]
            player["hero_drafter"] = row["Hero Drafter"]

            players.append(player)
        return sorted(players, key=lambda x: x["draft_value"], reverse=True)

def parse_playerlist_FHDL_csv(filename):
    with open(filename) as f:
        reader = csv.DictReader(f)

        players = []
        for row in reader:
            player = {}
            if not row["Name:"]:
                continue

            player["name"] = row["Name:"]
            player["draft_value"] = int(row["MMR:"])
            player["badge"] = row["MMR:"]
            player["dotabuff"] = row["Dotabuff:"]
            player["statement"] = row["Statement:"]
            player["pos1"] = row["Pos 1:"]
            player["pos2"] = row["Pos 2:"]
            player["pos3"] = row["Pos 3:"]
            player["pos4"] = row["Pos 4: "]
            player["pos5"] = row["Pos 5:"]

            players.append(player)
        return sorted(players, key=lambda x: x["draft_value"], reverse=True)



def arbitrary_formula(mmr_value):
    return 10000 - (mmr_value * 100)


def parse_captainlist_csv(filename):
    with open(filename) as f:
        reader = csv.DictReader(f)

        captains = []
        for row in reader:
            captain = {}
            if not row["name"]:
                continue

            captain["name"] = row["name"]
            mmr_value = float(
                sum(fractions.Fraction(s) for s in row["Draft Value"].split())
            )
            captain["captain_bank"] = arbitrary_formula(mmr_value)

            captains.append(captain)
        return sorted(captains, key=lambda x: x["captain_bank"], reverse=True)

def parse_captainlist_FHDL_csv(filename):
    with open(filename) as f:
        reader = csv.DictReader(f)

        captains = []
        for row in reader:
            captain = {}
            if not row["Name:"]:
                continue

            captain["name"] = row["Name:"]
            mmr_value = row["Money:"]
            captain["captain_bank"] = mmr_value

            captains.append(captain)
        return sorted(captains, key=lambda x: x["captain_bank"], reverse=True)


if __name__ == "__main__":
    playerlist = parse_playerlist_csv("test_playerlist.csv")
    pprint.pprint(playerlist)
    captainlist = parse_captainlist_csv("test_captainlist.csv")
    pprint.pprint(captainlist)
