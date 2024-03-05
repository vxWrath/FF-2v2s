import asyncio
import discord
from discord import app_commands, ui
from discord.ext import commands
from typing import Optional

from resources import MatchMaker, Object

class ViewTrophies(commands.Cog):
    def __init__(self, bot: MatchMaker):
        self.bot: MatchMaker = bot
        
    @app_commands.command(
        name="viewtrophies", 
        description="view your or another person's trophy count",
        extras = Object(defer_ephemerally=True, get_user_data=True)
    )
    @app_commands.describe(user="the user to view")
    async def viewtrophies(self, interaction: discord.Interaction[MatchMaker], user: Optional[discord.User]=None):
        user = user or interaction.user
        data = interaction.extras['users'][user.id]
        
        await interaction.followup.send(content=f"{user.mention} has **{data.trophies} trophies**", ephemeral=True)
        
async def setup(bot: MatchMaker):
    cog = ViewTrophies(bot)
    
    for command in cog.walk_app_commands():
        if hasattr(command, "callback"):
            setattr(command.callback, "__name__", f"{cog.qualified_name.lower()}_{command.callback.__name__}")
            setattr(command, "guild_only", True)
    
    await bot.add_cog(cog)