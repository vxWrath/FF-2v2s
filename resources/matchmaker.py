import asyncio
import aiohttp
import os
import sys
import colorlog
import pytesseract

import discord
from discord.app_commands import Command, CommandTree, errors
from discord.ext import commands
from google.cloud import vision_v1

intents = discord.Intents.none()
intents.guilds  = True
intents.members = True
intents.message_content = True

member_cache_flags = discord.MemberCacheFlags().none()
member_cache_flags.joined = True

from .database import Database
from .objects import Object
from .queue import Queue
from .roblox import RobloxClient
from .states import States

pytesseract.pytesseract.tesseract_cmd = 'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = f"credentials.json"

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
        
        self.production       = False if sys.platform == 'win32' else True
        self.external_session = aiohttp.ClientSession()
        self.database         = Database()
        self.queuer           = Queue(self)
        self.states           = States(self)

        self.vision_api       = vision_v1.ImageAnnotatorAsyncClient()
        
    async def setup_hook(self) -> None:
        self.loop.create_task(self.database.ping_loop())
        self.roblox_client = RobloxClient(self.external_session)

        await self.load_extensions()
        
        logger = colorlog.getLogger('bot')
        logger.info(f"Logged in - {self.user.name} ({self.application_id})")
        logger.info(f"Loaded {len([x for x in self.tree.walk_commands() if isinstance(x, Command)])} Commands")

        # adds the play panel to persistent views
        cog = self.get_cog('Events')
        cog.add_view()
        
    async def load_extensions(self):
        self._cogs_ = ["resources.utils", "resources.queue"]
        
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
        if interaction.guild and interaction.guild.unavailable:
            try:
                await interaction.response.send_message(
                    content = "<:fail:1136341671857102868>**| This server is unavailable. This is a discord issue.**", 
                    ephemeral = True
                )
            except discord.HTTPException:
                pass
            
            return False
        
        interaction.data   = Object(interaction.data)
        interaction.extras = Object(interaction.extras)
        extras             = interaction.command.extras if interaction.command else interaction.extras['extras']
        
        if extras.defer:
            await interaction.response.defer(ephemeral=False, thinking=extras.thinking or False)
        elif extras.defer_ephemerally:
            await interaction.response.defer(ephemeral=True, thinking=extras.thinking or False)
            
        if extras.user_data:
            try:
                async with asyncio.timeout(2):
                    interaction.extras.users = Object({
                        interaction.user.id: await self.client.database.produce_user(interaction.user.id)
                    })
                    
                    if interaction.data.resolved:
                        for user_id, user_data in (interaction.data.resolved.members or interaction.data.resolved.users or {}).items():
                            if user_data.get('bot', False) or user_data.get('user', {}).get('bot', False) or interaction.user.id == int(user_id):
                                continue
                            
                            interaction.extras.users[int(user_id)] = await self.client.database.produce_user(int(user_id))
                    
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass
        
        return True