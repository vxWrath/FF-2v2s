import asyncio
import os
import sys
import colorlog

import discord
from os import environ as env
from discord.app_commands import Command, CommandTree
from discord.ext import commands

intents = discord.Intents.none()
intents.guilds  = True
intents.members = True

member_cache_flags = discord.MemberCacheFlags().none()
member_cache_flags.joined = True

class MatchMaker(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix = [], # basically turns off prefix commands
            tree_cls = AppCommandTree,
            intents = intents,
            member_cache_flags = member_cache_flags,
            max_messages = None, # turns off the internal message cache
            chunk_guilds_at_startup = True # turn this off if the bot gets big
        )
        
        self.database = None
        
    async def setup_hook(self) -> None:
        await self.load_extensions()
        
        logger = colorlog.getLogger('bot')
        logger.info(f"Logged in - {self.user.name} ({self.application_id})")
        logger.info(f"Loaded {len([x for x in self.tree.walk_commands() if isinstance(x, Command)])} Commands")
        
        self.tree.copy_global_to(guild=discord.Object(id=1210700325619507240))
        await self.tree.sync(guild=discord.Object(id=1210700325619507240))
        
    async def load_extensions(self):
        self._cogs_ = []
        
        for cog in self._cogs_:
            try:
                await self.reload_extension(cog)
            except commands.ExtensionNotLoaded:
                await self.load_extension(cog)
        
        dont_load = []
        for dir_, _, files in os.walk('./commands'):
            for file in files:
                if not file.endswith('.py') or file in dont_load:
                    continue
                
                self._cogs_.append(dir_[2:].replace("\\" if sys.platform == 'win32' else '/', ".") + f".{file[:-3]}")
                
                try:
                    await self.reload_extension(self._cogs_[-1])
                except commands.ExtensionNotLoaded:
                    await self.load_extension(self._cogs_[-1])
                    
    async def unload_extensions(self):
        for i in range(0, len(self._cogs_)):
            try:
                await self.unload_extension(self._cogs_[i])
            except commands.ExtensionNotLoaded:
                pass
            
class AppCommandTree(CommandTree[MatchMaker]):
    async def interaction_check(self, interaction: discord.Interaction[MatchMaker]) -> bool:
        return True