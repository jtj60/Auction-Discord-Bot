import pytest
from unittest import mock

from draft import AuctionValidationError
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

    assert started_auction.machine.state == "nominating"


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
        print(e)


def test_add_player_from_command(started_auction):
    started_auction.player(
        message=mock.Mock(
            content="$player test 35",
            author=mock.Mock(id=ADMIN_IDS[0]),
        )
    )


def test_add_captain_from_command(started_auction):
    started_auction.captain(
        message=mock.Mock(
            content="$captain test 1000",
            author=mock.Mock(id=ADMIN_IDS[0]),
        )
    )
