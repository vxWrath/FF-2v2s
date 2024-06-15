import asyncio
import datetime
import discord
import collections
import numpy

from discord import app_commands
from discord.ext import commands

from resources import MatchMaker, Extras, Colors, Object, staff_only, Config

def is_thread(interaction: discord.Interaction) -> bool:
    config = Config.get()
    return interaction.channel.type == discord.ChannelType.private_thread and interaction.channel.parent.id == config.THREAD_CHANNEL

@app_commands.guild_only()
class ForceResult(commands.GroupCog, name="force", description="force cancel or force result of a match"):
    def __init__(self, bot: MatchMaker):
        self.bot = bot

    @app_commands.command(
        name="cancel", 
        description="forcefully cancel a match",
        extras=Extras(defer_ephemerally=True),
    )
    @app_commands.rename(match_id="match-id")
    @staff_only()
    async def force_cancel(self, interaction: discord.Interaction[MatchMaker], match_id: str):
        pass

    @app_commands.command(
        name="result", 
        description="forcefully set the result of a match",
        extras=Extras(defer_ephemerally=True),
    )
    @app_commands.rename(match_id="match-id")
    @staff_only()
    async def force_result(self, interaction: discord.Interaction[MatchMaker], match_id: str):
        pass
        
async def setup(bot: MatchMaker):
    cog = ForceResult(bot)
    
    for command in cog.walk_app_commands():
        if hasattr(command, "callback"):
            setattr(command.callback, "__name__", f"{cog.qualified_name.lower()}_{command.callback.__name__}")
            setattr(command, "guild_only", True)
    
    await bot.add_cog(cog)