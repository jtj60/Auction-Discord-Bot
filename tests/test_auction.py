import pytest
from unittest import mock

from draft import AuctionValidationError
from draft import ClientMessageType
from draft import InsufficientFundsError
from draft import TooLowBidError
from draft import BidAgainstSelfError
from auction import Auction
from auction import ADMIN_IDS
from lot import TWO_CAPTAINS_MODE_TIMER


@pytest.fixture
def started_auction():
    db = {}
    auction = Auction(db=db)
    auction.bootstrap_from_testlists()
    auction.start(
        message=mock.Mock(
            content="!start",
            author=mock.Mock(id=ADMIN_IDS[0]),
        )
    )
    return auction


@pytest.fixture
def running_auction(started_auction):
    started_auction.nominate(
        message=mock.Mock(
            content="!nominate toth Cev",
            author=mock.Mock(id=ADMIN_IDS[0]),
        )
    )

    bid_successful = started_auction.bid(
        message=mock.Mock(
            content="!bid 100 Cev",
            author=mock.Mock(id=ADMIN_IDS[0]),
        )
    )
    assert bid_successful

    for _ in started_auction.run_current_lot():
        # Uneventful bid process :P
        pass
    started_auction.give_lot_to_winner()

    started_auction.nominate(
        message=mock.Mock(
            content="nominate yolksoup yfu",
            author=mock.Mock(id=ADMIN_IDS[0]),
        )
    )

    bid_successful = started_auction.bid(
        message=mock.Mock(
            content="!bid 100 yfu",
            author=mock.Mock(id=ADMIN_IDS[0]),
        )
    )
    assert bid_successful

    for _ in started_auction.run_current_lot():
        # Uneventful bid process :P
        pass
    started_auction.give_lot_to_winner()
    return started_auction


def test_auction_start(started_auction):
    assert started_auction.machine.state == "starting"

    assert len(started_auction.players) > 0
    assert len(started_auction.captains) > 0


def test_admin_nominate(started_auction):
    started_auction.nominate(
        message=mock.Mock(
            content="$nominate toth Cev",
            author=mock.Mock(id=ADMIN_IDS[0]),
        )
    )

    assert started_auction.machine.state == "bidding"


def test_admin_nominate_messy_name(started_auction):
    started_auction.nominate(
        message=mock.Mock(
            content="!nominate Linkdx {noflamevow} Cev",
            author=mock.Mock(id=ADMIN_IDS[0]),
        )
    )
    assert started_auction.current_lot.player == "Linkdx {noflamevow}"
    assert started_auction.machine.state == "bidding"


def test_admin_nominate_messy_player_messy_captain(started_auction):
    started_auction.nominate(
        message=mock.Mock(
            content="!nominate Linkdx {noflamevow} Vuvuzela Virtuoso Hans Rudolph",
            author=mock.Mock(id=ADMIN_IDS[0]),
        )
    )
    assert started_auction.current_lot.player == "Linkdx {noflamevow}"
    assert started_auction.current_lot.nominator == "Vuvuzela Virtuoso Hans Rudolph"
    assert started_auction.machine.state == "bidding"

def test_captain_nominate_messy_player(started_auction):
    captain = started_auction.get_next_captain()

    # https://stackoverflow.com/questions/62552148/how-to-mock-name-attribute-with-unittest-mock-magicmock-or-mock-classes
    author = mock.Mock()
    author.id = 0
    author.name = captain['name']

    started_auction.nominate(
        message=mock.Mock(
            content="$nominate Linkdx {noflamevow}",
            author=author,
        )
    )
    
    assert started_auction.current_lot.player == "Linkdx {noflamevow}"
    assert started_auction.machine.state == "bidding"


def test_nominate_whitespace_name(started_auction):
    (player,) = [
        player
        for player in started_auction.players
        if player["name"] == "ZombiesExpert "
    ]
    assert player
    started_auction.nominate(
        message=mock.Mock(
            content="!nominate ZombiesExpert Cev",
            author=mock.Mock(id=ADMIN_IDS[0]),
        )
    )

    assert started_auction.current_lot.player == "ZombiesExpert "
    assert started_auction.machine.state == "bidding"


def test_nominate_lowercase_name(started_auction):
    (player,) = [
        player for player in started_auction.players if player["name"] == "Scrub"
    ]
    assert player
    started_auction.nominate(
        message=mock.Mock(
            content="!nominate scrub Cev",
            author=mock.Mock(id=ADMIN_IDS[0]),
        )
    )

    assert started_auction.current_lot.player == "Scrub"
    assert started_auction.machine.state == "bidding"


def test_nominate_typo_raises_auction_error(started_auction):
    with pytest.raises(AuctionValidationError):
        started_auction.nominate(
            message=mock.Mock(
                content="!nominate typotypo Cev",
                author=mock.Mock(id=ADMIN_IDS[0]),
            )
        )


def test_admin_nominate_from_nonadmin_raises(started_auction):
    with pytest.raises(AuctionValidationError) as e:
        started_auction.nominate(
            message=mock.Mock(
                content="!nominate toth Cev",
                author=mock.Mock(id=0),
            )
        )


def test_add_player_from_command(started_auction):
    started_auction.player(
        message=mock.Mock(
            content="!player test 35",
            author=mock.Mock(id=ADMIN_IDS[0]),
        )
    )
    player = started_auction.search_player("test")
    assert player["name"] == "test"
    assert player["mmr"] == 35


def test_add_captain_from_command(started_auction):
    started_auction.captain(
        message=mock.Mock(
            content="!captain test 1000",
            author=mock.Mock(id=ADMIN_IDS[0]),
        )
    )


def test_bid_messy_name(started_auction):
    started_auction.nominate(
        message=mock.Mock(
            content="!nominate toth Cev",
            author=mock.Mock(id=ADMIN_IDS[0]),
        )
    )
    vuvu_name = "Vuvuzela Virtuoso Hans Rudolph"
    bid_successful = started_auction.bid(
        message=mock.Mock(
            content=f"!bid 100 {vuvu_name}",
            author=mock.Mock(id=ADMIN_IDS[0]),
        )
    )
    assert bid_successful
    assert started_auction.current_lot.current_bids[0]["captain_name"] == vuvu_name


def test_give_lot_to_winner_happycase(started_auction):
    started_auction.nominate(
        message=mock.Mock(
            content="!nominate toth Cev",
            author=mock.Mock(id=ADMIN_IDS[0]),
        )
    )

    starting_dollars = started_auction.search_captain("Cev")["dollars"]
    bid_successful = started_auction.bid(
        message=mock.Mock(
            content="!bid 100 Cev",
            author=mock.Mock(id=ADMIN_IDS[0]),
        )
    )
    assert bid_successful

    for _ in started_auction.run_current_lot():
        # Uneventful bid process :P
        pass

    winning_bid = started_auction.current_lot.winning_bid
    assert winning_bid["amount"] == 100
    assert winning_bid["captain"] == "Cev"
    assert winning_bid["player"] == "toth"

    completed_lot = started_auction.give_lot_to_winner()

    captain = started_auction.search_captain("Cev")
    assert captain["dollars"] + completed_lot.amount_paid == starting_dollars
    assert started_auction.nominations[-1].lot_id == completed_lot.lot_id
    player = started_auction.search_player("toth")
    assert player["is_picked"]

    assert started_auction.machine.state == "nominating"


def _run_bids(auction, bids):
    for bid in bids:
        success = auction.bid(
            message=mock.Mock(
                content=bid,
                author=mock.Mock(id=ADMIN_IDS[0]),
            )
        )
        assert success


def test_give_lot_to_winner_multiple_bids(started_auction):
    started_auction.nominate(
        message=mock.Mock(
            content="!nominate toth Cev",
            author=mock.Mock(id=ADMIN_IDS[0]),
        )
    )

    starting_dollars = started_auction.search_captain("yfu")["dollars"]
    _run_bids(
        started_auction,
        ["!bid 100 Cev", "!bid 150 yfu", "!bid 200 Cev", "!bid 300 yfu"],
    )

    for _ in started_auction.run_current_lot():
        # Uneventful bid process :P
        pass

    winning_bid = started_auction.current_lot.winning_bid
    assert winning_bid["amount"] == 300
    assert winning_bid["captain"] == "yfu"
    assert winning_bid["player"] == "toth"

    completed_lot = started_auction.give_lot_to_winner()

    captain = started_auction.search_captain("yfu")
    assert captain["dollars"] + completed_lot.amount_paid == starting_dollars
    assert started_auction.current_lot is None


def test_bid_below_minimum_raises(started_auction):
    started_auction.nominate(
        message=mock.Mock(
            content="!nominate toth Cev",
            author=mock.Mock(id=ADMIN_IDS[0]),
        )
    )
    _run_bids(started_auction, ["!bid 100 Cev"])

    with pytest.raises(TooLowBidError) as e:
        started_auction.bid(
            message=mock.Mock(
                content="!bid 100 yfu",
                author=mock.Mock(id=ADMIN_IDS[0]),
            )
        )


def test_bid_insufficient_funds(started_auction):
    started_auction.nominate(
        message=mock.Mock(
            content="!nominate toth Cev",
            author=mock.Mock(id=ADMIN_IDS[0]),
        )
    )
    starting_dollar = int(started_auction.search_captain("yfu")["dollars"])

    with pytest.raises(InsufficientFundsError) as e:
        started_auction.bid(
            message=mock.Mock(
                content=f"!bid {starting_dollar + 1} yfu",
                author=mock.Mock(id=ADMIN_IDS[0]),
            )
        )


def test_cant_bid_against_yourself(started_auction):
    started_auction.nominate(
        message=mock.Mock(
            content="!nominate toth Cev",
            author=mock.Mock(id=ADMIN_IDS[0]),
        )
    )

    _run_bids(started_auction, ["!bid 100 Cev"])
    with pytest.raises(BidAgainstSelfError) as e:
        started_auction.bid(
            message=mock.Mock(
                content="!bid 105 Cev",
                author=mock.Mock(id=ADMIN_IDS[0]),
            )
        )


def test_detect_two_captains_mode(started_auction):
    started_auction.nominate(
        message=mock.Mock(
            content="!nominate toth Cev",
            author=mock.Mock(id=ADMIN_IDS[0]),
        )
    )

    bids_to_make = [
        "!bid 100 Cev",
        "!bid 101 yfu",
        "!bid 103 Cev",
        "!bid 104 yfu",
        "!bid 105 Cev",
        "!bid 106 yfu",
        "!bid 107 Cev",
        "!bid 108 yfu",
        "!bid 109 Cev",
        "!bid 110 yfu",
        "!bid 111 Cev",
        "!bid 112 yfu",
        "!bid 113 Cev",
        "!bid 114 yfu",
        "!bid 115 Cev",
        "!bid 116 yfu",
    ]

    for time_remaining in started_auction.run_current_lot():
        if bids_to_make and len(bids_to_make) < 6:
            assert (
                time_remaining == TWO_CAPTAINS_MODE_TIMER - 1
            )  # minus 1 because we've already run one second before it gets yielded
        elif not bids_to_make:
            assert time_remaining < TWO_CAPTAINS_MODE_TIMER

        # Uneventful bid process :P
        if time_remaining > 0 and bids_to_make:
            bid = bids_to_make.pop(0)
            success = started_auction.bid(
                message=mock.Mock(
                    content=bid,
                    author=mock.Mock(id=ADMIN_IDS[0]),
                )
            )
            assert success

            if len(bids_to_make) < 6:
                # inserting the bid will change the timer
                assert (
                    started_auction.current_lot.time_remaining
                    == TWO_CAPTAINS_MODE_TIMER
                )


def test_pop_nomination(running_auction):
    player = running_auction.search_player("yolksoup")
    assert player["is_picked"]
    captain = running_auction.search_captain("yfu")
    starting_dollars = captain["dollars"]
    assert running_auction.get_next_captain()["name"] != "yfu"

    popped_nomination = running_auction.pop_recent_nomination(0)
    assert popped_nomination.player_name == "yolksoup"
    player = running_auction.search_player("yolksoup")
    assert not player["is_picked"]

    captain = running_auction.search_captain("yfu")

    assert captain["dollars"] == starting_dollars + popped_nomination.amount_paid

    assert running_auction.get_next_captain()["name"] == "yfu"
