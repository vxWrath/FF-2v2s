from typing import Any, Optional

import discord
from colorthief import ColorThief
from discord.ext.commands import Bot as MatchMaker

from .objects import Object

class BaseView(discord.ui.View):
    def __init__(self, timeout: int, interaction: Optional[discord.Interaction[MatchMaker]]=None, extras: Optional[Object]=None):
        super().__init__(timeout=timeout)
        
        self.interaction = interaction
        self.extras      = extras or Object({})
        
    async def interaction_check(self, interaction: discord.Interaction[MatchMaker]) -> bool:
        if interaction.channel.type == discord.ChannelType.private:
            return True
        
        if self.extras.custom_id_data and interaction.data['custom_id'].split(':')[0] in self.extras.custom_id_data.keys():
            interaction.extras['extras'] = self.extras.custom_id_data[interaction.data['custom_id'].split(':')[0]]
        else:
            interaction.extras['extras'] = self.extras
        
        if not await interaction.client.tree.interaction_check(interaction):
            return False
        
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
    
class BaseModal(discord.ui.Modal):
    def __init__(self, title: str, timeout: int, interaction: Optional[discord.Interaction[MatchMaker]]=None, extras: Optional[Object]=None):
        super().__init__(title=title, timeout=timeout)
        
        self.interaction = interaction
        self.extras      = extras or Object({})
        
    async def interaction_check(self, interaction: discord.Interaction[MatchMaker]) -> bool:
        if interaction.channel.type == discord.ChannelType.private:
            return True
        
        interaction.extras['extras'] = self.extras
        return await interaction.client.tree.interaction_check(interaction)
        
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