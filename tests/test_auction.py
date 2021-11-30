import pytest
from unittest import mock

from draft import AuctionValidationError
from draft import ClientMessageType
from draft import InsufficientFundsError
from draft import TooLowBidError
from auction import Auction
from auction import ADMIN_IDS


@pytest.fixture
def started_auction():
    db = {}
    auction = Auction(db=db)
    auction.bootstrap_from_testlists()
    auction.start(
        message=mock.Mock(
            content="$start",
            author=mock.Mock(id=ADMIN_IDS[0]),
        )
    )
    return auction


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
            content="$nominate Linkdx {noflamevow} Cev",
            author=mock.Mock(id=ADMIN_IDS[0]),
        )
    )
    assert started_auction.current_lot.player == "Linkdx {noflamevow}"
    assert started_auction.machine.state == "bidding"

def test_admin_nominate_messy_player_messy_captain(started_auction):
    started_auction.nominate(
        message=mock.Mock(
            content="$nominate Linkdx {noflamevow} Vuvuzela Virtuoso Hans Rudolph",
            author=mock.Mock(id=ADMIN_IDS[0]),
        )
    )
    assert started_auction.current_lot.player == "Linkdx {noflamevow}"
    assert started_auction.current_lot.nominator == "Vuvuzela Virtuoso Hans Rudolph"
    assert started_auction.machine.state == "bidding"


def test_nominate_typo_raises_auction_error(started_auction):
    with pytest.raises(AuctionValidationError):
        started_auction.nominate(
            message=mock.Mock(
                content="$nominate typotypo Cev",
                author=mock.Mock(id=ADMIN_IDS[0]),
            )
        )


def test_admin_nominate_from_nonadmin_raises(started_auction):
    with pytest.raises(AuctionValidationError) as e:
        started_auction.nominate(
            message=mock.Mock(
                content="$nominate toth Cev",
                author=mock.Mock(id=0),
            )
        )

def test_add_player_from_command(started_auction):
    started_auction.player(
        message=mock.Mock(
            content="$player test 35",
            author=mock.Mock(id=ADMIN_IDS[0]),
        )
    )
    player = started_auction.search_player("test")
    assert player['name'] == 'test'
    assert player['mmr'] == 35


def test_add_captain_from_command(started_auction):
    started_auction.captain(
        message=mock.Mock(
            content="$captain test 1000",
            author=mock.Mock(id=ADMIN_IDS[0]),
        )
    )

def test_bid_messy_name(started_auction):
    started_auction.nominate(
        message=mock.Mock(
            content="$nominate toth Cev",
            author=mock.Mock(id=ADMIN_IDS[0]),
        )
    )
    vuvu_name = "Vuvuzela Virtuoso Hans Rudolph"
    bid_successful = started_auction.bid(
        message=mock.Mock(
            content=f"$bid 100 {vuvu_name}",
            author=mock.Mock(id=ADMIN_IDS[0]),
        )

    )
    assert bid_successful
    assert started_auction.current_lot.current_bids[0]['captain_name'] == vuvu_name

def test_give_lot_to_winner_happycase(started_auction):
    started_auction.nominate(
        message=mock.Mock(
            content="$nominate toth Cev",
            author=mock.Mock(id=ADMIN_IDS[0]),
        )
    )

    starting_dollars = started_auction.search_captain("Cev")['dollars']
    bid_successful = started_auction.bid(
        message=mock.Mock(
            content="$bid 100 Cev",
            author=mock.Mock(id=ADMIN_IDS[0]),
        )

    )
    assert bid_successful
    
    for _ in started_auction.run_current_lot():
        # Uneventful bid process :P
        pass

    winning_bid = started_auction.current_lot.winning_bid
    assert winning_bid['amount'] == 100
    assert winning_bid['captain'] == "Cev"
    assert winning_bid['player'] == "toth"

    completed_lot = started_auction.give_lot_to_winner()

    captain = started_auction.search_captain("Cev")
    assert captain['dollars'] + completed_lot.amount_paid == starting_dollars
    assert started_auction.nominations[-1].lot_id == completed_lot.lot_id
    assert started_auction.search_player('toth') is None

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
            content="$nominate toth Cev",
            author=mock.Mock(id=ADMIN_IDS[0]),
        )
    )

    starting_dollars = started_auction.search_captain("yfu")['dollars']
    _run_bids(started_auction, ["$bid 100 Cev", "$bid 150 yfu", "$bid 200 Cev", "$bid 300 yfu"])

    for _ in started_auction.run_current_lot():
        # Uneventful bid process :P
        pass

    winning_bid = started_auction.current_lot.winning_bid
    assert winning_bid['amount'] == 300
    assert winning_bid['captain'] == "yfu"
    assert winning_bid['player'] == "toth"

    completed_lot = started_auction.give_lot_to_winner()

    captain = started_auction.search_captain("yfu")
    assert captain['dollars'] + completed_lot.amount_paid == starting_dollars

def test_bid_below_minimum_raises(started_auction):
    started_auction.nominate(
        message=mock.Mock(
            content="$nominate toth Cev",
            author=mock.Mock(id=ADMIN_IDS[0]),
        )
    )
    _run_bids(started_auction, ["$bid 100 Cev"])

    with pytest.raises(TooLowBidError) as e:
        started_auction.bid(
            message=mock.Mock(
                content="$bid 100 yfu",
                author=mock.Mock(id=ADMIN_IDS[0]),
            )
        )

def test_bid_insufficient_funds(started_auction):
    started_auction.nominate(
        message=mock.Mock(
            content="$nominate toth Cev",
            author=mock.Mock(id=ADMIN_IDS[0]),
        )
    )
    starting_dollar = int(started_auction.search_captain("yfu")['dollars'])

    with pytest.raises(InsufficientFundsError) as e:
        started_auction.bid(
            message=mock.Mock(
                content=f"$bid {starting_dollar + 1} yfu",
                author=mock.Mock(id=ADMIN_IDS[0]),
            )
        )