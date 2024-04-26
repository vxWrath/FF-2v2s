import discord

from discord import app_commands
from discord.ext import commands

from resources import MatchMaker, Object, Extras, send_thread_log

class Test(commands.Cog):
    def __init__(self, bot: MatchMaker):
        self.bot: MatchMaker = bot
        
    @app_commands.command(
        name="test", 
        description="test command",
        extras=Extras(defer_ephemerally=True),
    )
    async def fillqueue(self, interaction: discord.Interaction[MatchMaker]):
        thread  = interaction.guild.get_thread(1232532164910907423)
        matchup = await interaction.client.database.get_match_by_thread(thread.id)
        
        await send_thread_log(matchup, thread)
        await interaction.followup.send(content="done")
        
async def setup(bot: MatchMaker):
    cog = Test(bot)
    
    for command in cog.walk_app_commands():
        if hasattr(command, "callback"):
            setattr(command.callback, "__name__", f"{cog.qualified_name.lower()}_{command.callback.__name__}")
            setattr(command, "guild_only", False)
    
    await bot.add_cog(cog)