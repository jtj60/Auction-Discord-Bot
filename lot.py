import asyncio


async def timer(t):
    for i in range(t, 0, -1):
        await asyncio.sleep(1)
        # do countdown logic
        while i >= 20 and i % 20 == 0:
            yield i
        if i <= 5:
            yield

INITIAL_BID_TIMER_DEFAULT = 60
LOT_TIMING_STRUCTURE = [35, 30, 20, 15, 15, 15, 15, 10, 10]
TWO_CAPTAINS_MODE_TIMER = 6


class Lot:
    def __init__(self, player, nominator, current_bids=None):
        if current_bids is None:
            self.current_bids = []
        self.player = player
        self.nominator = nominator
        self.time_remaining = None
        self.winning_bid = None
        self.is_paused = False

    def to_dict(self):
        return dict(
            player=self.player,
            current_bids=self.current_bids,
            nominator=self.nominator,
        )

    def from_dict(self, d):
        return Lot(**d)

    def determine_winner(self):
        if not self.current_bids:
            return dict(
                captain=self.nominator,
                amount=0,
                player=self.player,
            )
        else:
            # For live auction
            winning_bid = sorted(
                self.current_bids,
                key=lambda x: x["amount"],
                reverse=True,
            )[0]
            return dict(
                captain=winning_bid["captain_name"],
                amount=winning_bid["amount"],
                player=self.player,
            )

    def add_bid(self, bid):
        self.current_bids.append(bid)
        time_remaining_idx = len(self.current_bids) - 1
        self.time_remaining = LOT_TIMING_STRUCTURE[
            min(time_remaining_idx, len(LOT_TIMING_STRUCTURE) - 1)
        ]
        if self._detect_two_captains_mode():
            self.time_remaining = TWO_CAPTAINS_MODE_TIMER
        return self.time_remaining

    def _detect_two_captains_mode(self):
        recent_bids = self.current_bids[-6:]
        if len(recent_bids) < 6:
            return False
        captains = [bid["captain_name"] for bid in recent_bids]
        if len(set(captains)) <= 2:
            return True
        return False

    @property
    def current_max_bid(self):
        if not self.current_bids:
            return None
        else:
            return sorted(self.current_bids, key=lambda x: x["amount"])[-1]

    def run_lot(self, initial_timer=INITIAL_BID_TIMER_DEFAULT):
        self.time_remaining = initial_timer
        while self.time_remaining > 0:
            if self.is_paused:
                yield None
                continue
            self.time_remaining = self.time_remaining - 1
            # TODO: only yield sometimes?
            yield self.time_remaining

        self.winning_bid = self.determine_winner()
