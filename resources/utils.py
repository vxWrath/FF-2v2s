from typing import Any, Optional

import discord
from colorthief import ColorThief
from discord.ext.commands import Bot as MatchMaker

from .models import Extras
from .objects import Object

class BaseView(discord.ui.View):
    def __init__(self, timeout: int, interaction: Optional[discord.Interaction[MatchMaker]]=None, extras: Optional[Extras]=None):
        super().__init__(timeout=timeout)
        
        self.interaction = interaction
        self.extras      = extras or Extras()
        
    async def interaction_check(self, interaction: discord.Interaction[MatchMaker]) -> bool:
        if self.extras.custom_id and interaction.data['custom_id'].split(':')[0] in self.extras.custom_id.keys():
            interaction.extras['extras'] = self.extras.custom_id[interaction.data['custom_id'].split(':')[0]]
        else:
            interaction.extras['extras'] = self.extras

        if not await interaction.client.tree.interaction_check(interaction):
            return False
        
        if interaction.channel.type == discord.ChannelType.private:
            return True
        
        if hasattr(self, "check_func"):
            return await self.check_func(interaction)
        elif self.interaction.user != interaction.user:
            try:
                await interaction.response.send_message(content="❌ **You don't have permission to do that**", ephemeral=True)
            except discord.HTTPException:
                pass
            
            return False
        
        return True
    
    async def on_timeout(self) -> None:
        if not self.interaction:
            return
                
        for child in self.children:
            child.disabled = True
            
        try:
            await self.interaction.edit_original_response(content="**This message has expired**", view=self)
        except discord.HTTPException:
            pass
        
    async def on_error(self, interaction: discord.Interaction[MatchMaker], error: Exception, _: discord.ui.Item[Any]) -> None:
        return await interaction.client.tree.on_error(interaction, error)
    
    async def cancel_view(self):
        self.stop()

        if not self.interaction:
            return
                
        try:
            await self.interaction.edit_original_response(content="❌ **Canceled**", view=None, embed=None)
        except discord.HTTPException:
            pass
    
class BaseModal(discord.ui.Modal):
    def __init__(self, title: str, timeout: int, interaction: Optional[discord.Interaction[MatchMaker]]=None, extras: Optional[Extras]=None):
        super().__init__(title=title, timeout=timeout)
        
        self.interaction = interaction
        self.extras      = extras or Extras()
        
    async def interaction_check(self, interaction: discord.Interaction[MatchMaker]) -> bool:
        interaction.extras['extras'] = self.extras
        
        if not await interaction.client.tree.interaction_check(interaction):
            return False
        return True
        
    async def on_timeout(self) -> None:
        if not self.interaction:
            return
                
        for child in self.children:
            child.disabled = True
            
        try:
            await self.interaction.edit_original_response(content="**This message has expired**", view=self)
        except discord.HTTPException:
            pass
        
    async def on_error(self, interaction: discord.Interaction, error: Exception):
        await interaction.client.tree.on_error(interaction, error)
        
class Colors:
    white   = discord.Color.from_str("#FFFFFF")
    blue    = discord.Color.from_str("#5896ff")
    blank   = discord.Color.from_str("#2B2D31")
    
    @staticmethod
    async def image_to_color(client: MatchMaker, file) -> discord.Color:
        if file is None:
            return Colors.blank
        
        try:
            if isinstance(file, discord.Asset):
                file  = await file.to_file()
                
            image = ColorThief(file.fp)
            rgb   = await client.loop.run_in_executor(None, image.get_color, 1)
            
            return discord.Color.from_rgb(*rgb)
        except Exception:
            return Colors.blank
        
async def setup(bot: MatchMaker):
    pass