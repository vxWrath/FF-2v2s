import asyncio
import discord
import datetime
import re
from discord import app_commands, ui
from discord.ext import commands
from typing import Optional
import random
import uuid

from resources import MatchMaker, Object

class ClearStates(commands.Cog):
    def __init__(self, bot: MatchMaker):
        self.bot: MatchMaker = bot
        
    @app_commands.command(
        name="clearstates", 
        description="test command: clears player states within the queue/game system",
        extras = Object(defer_ephemerally=True)
    )
    async def fillqueue(self, interaction: discord.Interaction[MatchMaker]):
        interaction.client.states = Object({})
        await interaction.followup.send(content="done")
        
async def setup(bot: MatchMaker):
    cog = ClearStates(bot)
    
    for command in cog.walk_app_commands():
        if hasattr(command, "callback"):
            setattr(command.callback, "__name__", f"{cog.qualified_name.lower()}_{command.callback.__name__}")
            setattr(command, "guild_only", False)
    
    await bot.add_cog(cog)