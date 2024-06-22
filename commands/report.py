import asyncio
import datetime
import discord

from discord import app_commands, ui
from discord.ext import commands
from typing import Literal

from resources import MatchMaker, Object, Extras, BaseView, Match, DeleteMessageView, send_thread_log, Config, match_thread_only

class Report(commands.Cog):
    def __init__(self, bot: MatchMaker):
        self.bot: MatchMaker = bot
        
    @app_commands.command(
        name="report", 
        description="challenge a call or report someone for dodging",
        extras=Extras(defer_ephemerally=True, user_data=True),
    )
    @match_thread_only()
    async def report(self, interaction: discord.Interaction[MatchMaker], action: Literal['challenge call', 'report dodging']):
        data   = interaction.extras['users'][interaction.user.id]
        rblx   = await self.bot.roblox_client.get_user(data.roblox_id)
        
        if not rblx:
            return await interaction.followup.send(content=f"⚠️ **You are not verified. Run /account to verify**", view=DeleteMessageView(interaction, 60))
        
        matchup = await interaction.client.database.get_match_by_thread(interaction.channel.id)
        
        if not matchup:
            return await interaction.followup.send(content=f"❌ **I couldn't find the matchup within this thread**")
        
async def setup(bot: MatchMaker):
    cog = Report(bot)
    
    for command in cog.walk_app_commands():
        if hasattr(command, "callback"):
            setattr(command.callback, "__name__", f"{cog.qualified_name.lower()}_{command.callback.__name__}")
            setattr(command, "guild_only", False)
    
    await bot.add_cog(cog)