from asyncio import Task

class Lot(Task):
  def __init__(self, player):
    self.current_bids = []
    self.player = player['name']