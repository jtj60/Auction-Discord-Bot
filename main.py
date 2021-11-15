from discord.ext import commands

client = commands.Bot(command_prefix = '#')

@client.event
async def on_command_error(ctx, error):
  if isinstance(error, commands.MissingRequiredArgument):
    await ctx.send('Wrong input, try again.')

@client.event
async def on_ready():
  print('Bot is ready.')

class AuctionBot(commands.Cog): 
  def __init__(self, client):
    self.admin = 411342580887060480
    self.client = client

  commands.command()
  async def hello(self, ctx):
    await ctx.send('pog')

client.add_cog(AuctionBot(client))



#BOT TOKEN
client.run('OTAxMjQ0MzMxOTA0NjIyNTky.YXNDMQ.eYTemC4HYrttRp3I-luGroViwpg')



