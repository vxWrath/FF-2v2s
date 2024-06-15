import discord

from discord import app_commands
from discord.ext import commands

from resources import MatchMaker, Object, Extras, States

class ClearStates(commands.Cog):
    def __init__(self, bot: MatchMaker):
        self.bot: MatchMaker = bot
        
    @app_commands.command(
        name="clearstates", 
        description="test command: clears player states within the queue/game system",
        extras=Extras(defer_ephemerally=True),
    )
    async def fillqueue(self, interaction: discord.Interaction[MatchMaker]):
        interaction.client.states = States(interaction.client)
        await interaction.followup.send(content="done")
        
async def setup(bot: MatchMaker):
    cog = ClearStates(bot)
    
    for command in cog.walk_app_commands():
        if hasattr(command, "callback"):
            setattr(command.callback, "__name__", f"{cog.qualified_name.lower()}_{command.callback.__name__}")
            setattr(command, "guild_only", False)
    
    await bot.add_cog(cog)