import asyncio
import discord
import datetime
import re
from discord import app_commands, ui
from discord.ext import commands
from typing import Optional
import random
import uuid

from resources import MatchMaker, Object, User, RobloxUser, BaseView, BaseModal, Colors, Region

class Cancel(commands.Cog):
    def __init__(self, bot: MatchMaker):
        self.bot: MatchMaker = bot
        
    @app_commands.command(
        name="cancel", 
        description="cancel match making",
        extras = Object(defer_ephemerally=True, get_user_data=True)
    )
    async def cancel(self, interaction: discord.Interaction[MatchMaker]):
        session = [
            x for x in interaction.client.queuer.queue 
            if x.team.player_one.id == interaction.user.id
            or x.team.player_two.id == interaction.user.id
        ]
        
        if not session:
            return await interaction.followup.send(content=f"❌ **You are not in the match making queue**", ephemeral=True)
        
        session = session[0]
        session.future.set_result(Object(canceled_by=interaction.user))
        interaction.client.queuer.queue.remove(session)
        
        await interaction.followup.send(content=f"**Match making canceled**", ephemeral=True)
        
async def setup(bot: MatchMaker):
    cog = Cancel(bot)
    
    for command in cog.walk_app_commands():
        if hasattr(command, "callback"):
            setattr(command.callback, "__name__", f"{cog.qualified_name.lower()}_{command.callback.__name__}")
            setattr(command, "guild_only", False)
    
    await bot.add_cog(cog)