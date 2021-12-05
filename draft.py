from replit import db as replit_db

from transitions import Machine
import uuid
import slugify

from collections import namedtuple
from lot import Lot
import playerlist_util


class ClientMessageType:
    CHANNEL_MESSAGE = 0
    REACT = 1
    DIRECT_MESSAGE = 2


ClientMessage = namedtuple("ClientMessage", ["type", "data"])
Nomination = namedtuple(
    "Nomination",
    ["lot_id", "player_name", "player_mmr", "nominator", "captain", "amount_paid"],
)

ADMIN_IDS = [
    411342580887060480,  # toth
    181700384279101440,  # fspoon
    135543804668280832,  # kden
]


class AuctionValidationError(Exception):
    def __init__(self, client_message):
        super().__init__()
        self.client_message = client_message


class InsufficientFundsError(AuctionValidationError):
    pass


class TooLowBidError(AuctionValidationError):
    pass


class BidAgainstSelfError(AuctionValidationError):
    pass


class Auction:
    def __init__(self, db=None):
        self.debug = False
        if db is not None:
            self.db = db
        else:
            self.db = replit_db

        self.states = [
            "asleep",
            "starting",
            "nominating",
            "bidding",
            "pausing",
            "ending",
        ]
        self.machine = Machine(states=self.states, initial="asleep")
        self.machine.add_transition("start_machine", "asleep", "starting")
        self.machine.add_transition("nom_from_start", "starting", "nominating")
        self.machine.add_transition("bid_from_nom", "nominating", "bidding")
        self.machine.add_transition("nom_from_bid", "bidding", "nominating")
        self.machine.add_transition("end_from_bid", "bidding", "ending")

        self.captains = []
        self.players = []
        self.bids = []
        self.nominations = []

        self.current_lot = None
        self.populate_from_db()

    def populate_from_db(self):
        if "captains" in self.db.keys():
            self.captains = self.db["captains"]
        if "players" in self.db.keys():
            self.players = self.db["players"]
        if "bids" in self.db.keys():
            self.bids = self.db["bids"]
        if "nominations" in self.db.keys():
            self.bids = self.db["nominations"]

    def persist_key(self, key):
        self.db[key] = getattr(self, key)

    def delete_db(self):
        for key in ["captains", "players", "bids", "captain_order", "nominations"]:
            try:
                setattr(self, key, [])
                del self.db[key]
            except KeyError:
                pass

    def addCaptain(self, name, dollars):
        if self.search_captain(name):
            return False
        captain = {"name": name, "dollars": dollars, "slug": slugify.slugify(name)}
        self.captains.append(captain)
        self.db["captains"] = self.captains
        return True

    def search_captain(self, name):
        for captain in self.captains:
            if captain["name"] == name:
                return captain
            if slugify.slugify(captain["name"]) == slugify.slugify(name):
                return captain
        return None

    def search_player(self, name):
        for player in self.players:
            if player["name"] == name:
                return player
            if slugify.slugify(player["name"]) == slugify.slugify(name):
                return player
        return None

    def clearCaptains(self):
        self.captains = []
        self.db["captains"] = self.captains

    def addPlayer(
        self,
        name,
        mmr,
        badge="",
        opendota="",
        dotabuff="",
        statement="",
        pos1="",
        pos2="",
        pos3="",
        pos4="",
        pos5="",
        hero_drafter="",
        is_picked=False,
    ):
        if self.checkPlayer(name):
            return False
        player = {
            "name": name,
            "mmr": mmr,
            "badge": badge,
            "opendota": opendota,
            "dotabuff": dotabuff,
            "statement": statement,
            "pos1": pos1,
            "pos2": pos2,
            "pos3": pos3,
            "pos4": pos4,
            "pos5": pos5,
            "hero_drafter": hero_drafter,
            "is_picked": is_picked,
        }
        self.players.append(player)
        self.db["players"] = self.players
        return True

    def removePlayer(self, name):
        # TODO: This function clearly does not work
        if self.checkPlayer(name):
            self.players.remove()
            self.db["players"] = self.players
            return True
        return False

    def checkPlayer(self, name):
        for player in self.players:
            if player["name"] == name:
                return True
        return False

    def clearPlayers(self):
        self.players = []
        self.db["players"] = self.players

    def is_admin(self, message):
        if message.author.id in ADMIN_IDS or self.debug:
            return True
        return False

    def get_next_captain(self):
        return self.db["captain_nominate_order"][0]

    def bootstrap_from_testlists(self):
        playerlist = playerlist_util.parse_playerlist_csv("test_playerlist.csv")
        captainlist = playerlist_util.parse_captainlist_csv("test_captainlist.csv")

        for captain in captainlist:
            self.addCaptain(captain["name"], captain["captain_bank"])

        for player in playerlist:
            self.addPlayer(
                player["name"],
                player["draft_value"],
                player["badge"],
                player["opendota"],
                player["dotabuff"],
                player["statement"],
                player["pos1"],
                player["pos2"],
                player["pos3"],
                player["pos4"],
                player["pos5"],
                player["hero_drafter"],
                is_picked=False,
            )

    def populate_captain_nominate_order(self):
        captains = sorted(self.db["captains"], key=lambda x: x["dollars"], reverse=True)
        self.db["captain_nominate_order"] = captains * 4

    def start(self, message):
        if self.is_admin(message):
            self.machine.start_machine()
            self.populate_captain_nominate_order()
        else:
            raise AuctionValidationError(
                ClientMessage(
                    ClientMessageType.CHANNEL_MESSAGE,
                    "You are not an admin.",
                )
            )

    def autonominate(self, next_eligible_captain):
        pickable_players = [
            player for player in self.db["players"] if not player["is_picked"]
        ]
        players_by_mmr = sorted(pickable_players, key=lambda x: x["mmr"], reverse=True)
        player_to_autonominate = players_by_mmr[0]
        self.current_lot = Lot(
            player_to_autonominate["name"], next_eligible_captain["name"]
        )
        return self.current_lot

    def _validate_captain(self, message):
        message_body = self.parse_message_for_names(message)
        author_name = message.author.name
        captain = self.search_captain(message_body["captain"])
        if captain is None:
            return None

        if author_name != captain["name"]:
            if not self.is_admin(message):
                return None
        return captain

    def _validate_bid_amount(self, bid_amount, captain):
        if bid_amount < 0:
            return None

        if bid_amount > captain["dollars"]:
            raise InsufficientFundsError(
                client_message=ClientMessage(
                    ClientMessageType.REACT,
                    f"{captain['name']} doesn't have enough money to bid {bid_amount}.",
                )
            )

        current_max_bid = self.current_lot.current_max_bid

        if current_max_bid is None:
            return bid_amount

        if bid_amount <= current_max_bid["amount"]:
            raise TooLowBidError(
                client_message=ClientMessage(
                    ClientMessageType.REACT,
                    f"{bid_amount} is less than the current max bid.",
                )
            )
        if captain["name"] == current_max_bid["captain_name"]:
            raise BidAgainstSelfError(
                client_message=ClientMessage(
                    ClientMessageType.REACT,
                    f"You're already the highest bid",
                )
            )
        return bid_amount

    def bid(self, message):
        if self.machine.state != "bidding":
            print(f"Received bid in state {self.machine.state}, ignoring")
            return

        message_body = self.parse_message_for_names(message)
        captain = self._validate_captain(message)
        bid_amount = self._validate_bid_amount(message_body["amount"], captain)
        if bid_amount is None:
            raise AuctionValidationError(
                ClientMessage(
                    ClientMessageType.REACT,
                    "-",
                )
            )
            return
        if not self.current_lot:
            print("This shouldn't happen, in bidding state but no current lot")
        self.current_lot.add_bid(dict(captain_name=captain["name"], amount=bid_amount))
        return ClientMessage(ClientMessageType.REACT, "+")

    def nominate(self, message):
        message_body = self.parse_message_for_names(message)
        # TODO: Make sure this author was allowed to nominate
        nominated_on_behalf_of_captain = message.author.name
        if not message_body["player"]:
            raise AuctionValidationError(
                ClientMessage(
                    type=ClientMessageType.CHANNEL_MESSAGE,
                    data="That player is not in the system.",
                )
            )

        if message_body.get("captain") is not None:
            nominated_on_behalf_of_captain = message_body["captain"]
            if not self.is_admin(message):
                raise AuctionValidationError(
                    ClientMessage(
                        type=ClientMessageType.CHANNEL_MESSAGE,
                        data=f"Can't nominate {message_body['player']} on behalf of {nominated_on_behalf_of_captain}, not admin",
                    )
                )
            if not self.search_captain(nominated_on_behalf_of_captain):
                raise AuctionValidationError(
                    ClientMessage(
                        type=ClientMessageType.CHANNEL_MESSAGE,
                        data=f"Can't nominate {message_body['player']} on behalf of {nominated_on_behalf_of_captain}, not a captain",
                    )
                )
        else:
            next_eligible_captain = self.get_next_captain()
            if nominated_on_behalf_of_captain != next_eligible_captain["name"]:
                data = f"{nominated_on_behalf_of_captain} is not eligible to nominate at this time"
                raise AuctionValidationError(
                    ClientMessage(
                        type=ClientMessageType.CHANNEL_MESSAGE,
                        data=data,
                    )
                )

        if self.machine.state == "starting":
            self.machine.nom_from_start()

        self.current_lot = Lot(message_body["player"], nominated_on_behalf_of_captain)
        self.machine.bid_from_nom()
        return self.current_lot

    def clear_lot(self):
        self.current_lot = None

    def get_current_teams(self):
        teams_by_captain_name = {}
        for nomination in self.nominations:
            teams_by_captain_name.setdefault(nomination.captain, []).append(nomination)
        return teams_by_captain_name

    def give_lot_to_winner(self):
        winning_bid = self.current_lot.winning_bid
        player = self.search_player(winning_bid["player"])
        captain = self.search_captain(winning_bid["captain"])
        nomination = Nomination(
            lot_id=str(uuid.uuid4()),
            player_mmr=player["mmr"],
            player_name=player["name"],
            captain=captain["name"],
            nominator=self.current_lot.nominator,
            amount_paid=winning_bid["amount"],
        )

        # Housekeeping
        self.pop_captain_from_nominate_order()
        captain["dollars"] -= winning_bid["amount"]
        self.db["captians"] = self.captains
        self.nominations.append(nomination)
        self.persist_key("nominations")
        player["is_picked"] = True
        self.persist_key("players")

        self.current_lot = None

        return nomination

    def pop_captain_from_nominate_order(self):
        nominate_order = self.db["captain_nominate_order"]
        nominate_order.pop(0)
        self.db["captain_nominate_order"] = nominate_order

    def pop_recent_nomination(self, nomination_offset=0):
        if len(self.nominations) == 0:
            return None
        nomination = self.nominations.pop(len(self.nominations) - 1 - nomination_offset)
        self.persist_key("nominations")

        captain = self.search_captain(nomination.captain)
        captain["dollars"] += nomination.amount_paid
        self.db["captians"] = self.captains

        player = self.search_player(nomination.player_name)
        player["is_picked"] = False
        self.persist_key("players")
        self.db["captain_nominate_order"].insert(0, captain)
        return nomination

    def run_current_lot(self):
        for time_remaining in self.current_lot.run_lot():
            yield time_remaining

        self.machine.nom_from_bid()

    def checkNum(self, number):
        if type(number) == float:
            return True
        return False

    def parse_message_for_names(self, message):
        message_body = {
            "command": None,
            "amount": None,
            "player": None,
            "captain": None,
        }
        message_parts = message.content.split()
        if message_parts[0] == "$bid":
            message_body["command"] = "$bid"
            try:
                amount = int(message_parts[1])
                message_body["amount"] = amount
            except ValueError:
                return message_body

            if len(message_parts) > 2:
                name_parts = message_parts[2:]
                possible_name = " ".join(name_parts)
                captain = self.search_captain(possible_name)
                if captain:
                    message_body["captain"] = captain["name"]

            return message_body

        if message_parts[0] == "$nominate":
            message_body["command"] = "$nominate"

            name_parts = message_parts[1:]
            for i in range(len(name_parts)):
                player_name, captain_name = name_parts[:i], name_parts[i:]
                player_name = " ".join(player_name)
                captain_name = " ".join(captain_name)

                player = self.search_player(player_name)
                captain = self.search_captain(captain_name)
                if not player:
                    if captain:
                        message_body["captain"] == captain["name"]
                    continue
                message_body["player"] = player["name"]
                if captain:
                    message_body["captain"] = captain["name"]

                return message_body
            return message_body

    def player(self, message):
        message_parts = message.content.split()
        player_name = message_parts[1]
        if not self.is_admin(message):
            raise AuctionValidationError(
                ClientMessage(
                    type=ClientMessageType.CHANNEL_MESSAGE,
                    data=f"Can't add {player_name}, not an admin.",
                )
            )
        if self.checkPlayer(player_name):
            raise AuctionValidationError(
                ClientMessage(
                    type=ClientMessageType.CHANNEL_MESSAGE,
                    data=f"Can't add {player_name}, that player is already in the system.",
                )
            )
        if len(message_parts) > 2:
            player_mmr = float(message_parts[2])
            if not self.checkNum(player_mmr):
                raise AuctionValidationError(
                    ClientMessage(
                        type=ClientMessageType.CHANNEL_MESSAGE,
                        data=f"Can't add {player_name}, improper MMR formatting.",
                    )
                )
            if not self.addPlayer(player_name, player_mmr):
                raise AuctionValidationError(
                    ClientMessage(
                        type=ClientMessageType.CHANNEL_MESSAGE,
                        data=f"Error adding {player_name}.",
                    )
                )
        else:
            raise AuctionValidationError(
                ClientMessage(
                    type=ClientMessageType.CHANNEL_MESSAGE,
                    data=f"Can't add {player_name}, improper formatting: command requires player name and player mmr seperated by spaces.",
                )
            )

    def captain(self, message):
        message_parts = message.content.split()
        captain_name = message_parts[1]
        if not self.is_admin(message):
            raise AuctionValidationError(
                ClientMessage(
                    type=ClientMessageType.CHANNEL_MESSAGE,
                    data=f"Can't add {captain_name}, not an admin.",
                )
            )
            return
        if self.search_captain(captain_name):
            raise AuctionValidationError(
                ClientMessage(
                    type=ClientMessageType.CHANNEL_MESSAGE,
                    data=f"Can't add {captain_name}, that captain is already in the system.",
                )
            )
        if len(message_parts) > 2:
            captain_dollars = float(message_parts[2])
            if not self.checkNum(captain_dollars):
                raise AuctionValidationError(
                    ClientMessage(
                        type=ClientMessageType.CHANNEL_MESSAGE,
                        data=f"Can't add {captain_name}, improper MMR formatting.",
                    )
                )
            if not self.addCaptain(captain_name, captain_dollars):
                raise AuctionValidationError(
                    ClientMessage(
                        type=ClientMessageType.CHANNEL_MESSAGE,
                        data=f"Error adding {captain_name}.",
                    )
                )
        else:
            raise AuctionValidationError(
                ClientMessage(
                    type=ClientMessageType.CHANNEL_MESSAGE,
                    data=f"Can't add {captain_name}, improper formatting: command requires captain name and captain dollars seperated by spaces.",
                )
            )
