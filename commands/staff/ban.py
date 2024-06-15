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
    @admin_only()
    async def ban(self, interaction: discord.Interaction[MatchMaker], member: discord.Member, time: Optional[str]):
        pass
        
async def setup(bot: MatchMaker):
    cog = Ban(bot)
    
    for command in cog.walk_app_commands():
        if hasattr(command, "callback"):
            setattr(command.callback, "__name__", f"{cog.qualified_name.lower()}_{command.callback.__name__}")
            setattr(command, "guild_only", False)
    
    await bot.add_cog(cog)