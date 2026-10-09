from discord.ext import commands

# TODO: WORK ON THIS COG, IT'S NOT FINISHED YET
class Ticket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

async def setup(bot):
    await bot.add_cog(Ticket(bot))