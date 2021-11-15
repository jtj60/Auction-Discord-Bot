from replit import db

def addBid(name, amount):
  bids = db['bids']
  for bid in bids:
    if bid['name'] == name:
      return True
  bid = {'name': name, 'amount': amount}
  bids.append(bid)
  db['bids'] = bids
  return False

def removeBid(name):
  bids = db['bids']
  for bid in bids:
    if bid['name'] == name:
      bids.remove(bid)
      db['bids'] = bids
      return
  return

def clearBids():
  bids = db['bids']
  bids.clear()
  db['bids'] = bids

def bidCount():
  bids = db['bids']
  bidcount = len(bids)
  return bidcount

def highestBid():
  bids = db['bids']
  return max(bids['amount'])

def bidder():
  bids = db['bids']
  count = bidCount()
  if count >= 2:
    highBid = highestBid()
    removeBid(highBid['name'])
    db['bids'] = bids
    nextBid = highestBid()
    clearBids()
    vickreyPrice = nextBid['amount']
    highBid['amount'] = vickreyPrice
  
  elif count == 1:
    highBid == highestBid()
    highBid['amount'] = 0
  captains = db['captains']
  
  for captain in captains:
    if captain['name'] == highBid['name']:
      captain['dollars'] = captain['dollars'] - highBid['amount']
      db['captains'] = captains 
  return highBid
  


