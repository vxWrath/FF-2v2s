import asyncio
import discord
import re
from discord import app_commands, ui
from discord.ext import commands
from typing import Optional
import random
import uuid

from resources import MatchMaker, Object, User, RobloxUser, BaseView, BaseModal, Colors, Region

class TeammateSelection(BaseView):
    def __init__(self, interaction: discord.Interaction[MatchMaker], data: User, rblx: RobloxUser):
        super().__init__(120, interaction, Object(custom_id_data={
            "users": {"defer_ephemerally": True, "get_user_data": True},
            "cancel": {"defer": True},
        }))
        
        self.data = data
        self.rblx = rblx
        
    @ui.select(cls=ui.UserSelect, placeholder="Users", custom_id=f"users:{uuid.uuid4()}")
    async def users(self, interaction: discord.Interaction[MatchMaker], _: discord.SelectOption):
        other_user = self.users.values[0]
        
        if other_user.bot:
            return await interaction.followup.send(content=f"❌ **You can't queue up with a bot**", ephemeral=True)
        
        if other_user.id == interaction.user.id:
            return await interaction.followup.send(content=f"❌ **You can't queue up with yourself**", ephemeral=True)
        
        other_data = interaction.extras['users'][other_user.id]
        other_rblx = await interaction.client.roblox_client.get_user(other_data.roblox_id)
        
        if not other_rblx:
            return await interaction.followup.send(content=f"⚠️ **{other_user.mention} is not verified**", ephemeral=True)
        
        await interaction.edit_original_response(content="Queueing system not done...", view=None)
    
    @ui.button(label="Queue Solo", style=discord.ButtonStyle.blurple)
    async def solo(self, interaction: discord.Interaction[MatchMaker], _: discord.Button):
        await interaction.edit_original_response(content="Queueing system not done...", view=None)
    
    @ui.button(label="Cancel", style=discord.ButtonStyle.red, custom_id=f"cancel:{uuid.uuid4()}")
    async def cancel(self, interaction: discord.Interaction[MatchMaker], _: discord.Button):
        self.stop()
        await self.on_timeout()

class Queue(commands.Cog):
    def __init__(self, bot: MatchMaker):
        self.bot: MatchMaker = bot
        
    @app_commands.command(
        name="queue", 
        description="queue up for a 2v2 game",
        extras = Object(defer_ephemerally=True, get_user_data=True)
    )
    async def queue(self, interaction: discord.Interaction[MatchMaker]):
        data = interaction.extras['users'][interaction.user.id]
        rblx = await self.bot.roblox_client.get_user(data.roblox_id)
        
        if not rblx:
            return await interaction.followup.send(content = f"⚠️ **You are not verified. Run /account to verify**")
        
        await interaction.followup.send("**Select your 2v2 teammate below (They must be in this server)**", view=TeammateSelection(interaction, data, rblx))
        
async def setup(bot: MatchMaker):
    cog = Queue(bot)
    
    for command in cog.walk_app_commands():
        if hasattr(command, "callback"):
            setattr(command.callback, "__name__", f"{cog.qualified_name.lower()}_{command.callback.__name__}")
            setattr(command, "guild_only", False)
    
    await bot.add_cog(cog)