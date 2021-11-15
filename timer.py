import asyncio

async def timer(t):
  for i in range(t, 0, -1):
    await asyncio.sleep(1)
    if i <= 5:
      yield i
  