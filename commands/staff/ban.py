import discord

from discord import app_commands, ui
from discord.ext import commands
from typing import Optional

from resources import MatchMaker, Extras, admin_only

class Ban(commands.Cog):
    def __init__(self, bot: MatchMaker):
        self.bot: MatchMaker = bot

    @app_commands.command(
        name="playban", 
        description="ban someone from playing 2v2s",
        extras=Extras(defer_ephemerally=True, user_data=True),
    )
    @app_commands.choices(time=[
        app_commands.Choice(name="12 hours", value=43200),
        app_commands.Choice(name="1 day", value=86400),
        app_commands.Choice(name="3 days", value=259200),
        app_commands.Choice(name="7 days", value=604800),
        app_commands.Choice(name="14 days", value=1209600),
        app_commands.Choice(name="30 days", value=2592000),
        app_commands.Choice(name="60 days", value=51840000),
        app_commands.Choice(name="90 days", value=7776000),
        app_commands.Choice(name="Forever", value=0),
    ])
    @admin_only()
    async def ban(self, interaction: discord.Interaction[MatchMaker], member: discord.Member, time: app_commands.Choice[int]):
        pass
        
async def setup(bot: MatchMaker):
    cog = Ban(bot)
    
    for command in cog.walk_app_commands():
        if hasattr(command, "callback"):
            setattr(command.callback, "__name__", f"{cog.qualified_name.lower()}_{command.callback.__name__}")
            setattr(command, "guild_only", False)
    
    await bot.add_cog(cog)