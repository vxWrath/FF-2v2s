import asyncio
import discord
import re
from discord import app_commands, ui
from discord.ext import commands
from typing import Optional

from resources import MatchMaker, Object, User, RobloxUser, BaseView, BaseModal

ROBLOX_NAME = re.compile(r"^(?=^\w{3,20}$)[a-z0-9]+_?[a-z0-9]+$", flags=re.IGNORECASE)

word_bank = ['alice-blue', 'amaranth', 'amber', 'amethyst', 'apple-green', 'apple-red', 'apricot', 'aquamarine', 'azure', 'baby-blue', 'beige', 'brick-red', 'black', 'blue', 'blue-green', 'blue-violet', 'blush', 'bronze', 'brown', 'burgundy', 'carmine', 'cerise', 'cerulean', 'chocolate', 'cobalt-blue', 'coffee', 'copper', 'coral', 'crimson', 'cyan', 'desert-sand', 'electric-blue', 'emerald', 'gold', 'gray', 'green', 'indigo', 'ivory', 'jade', 'jungle-green', 'lavender', 'lemon', 'lilac', 'lime', 'magenta', 'maroon', 'navy-blue', 'olive', 'orange', 'orange-red', 'orchid', 'peach', 'pear', 'periwinkle', 'persian-blue', 'pink', 'plum', 'purple', 'raspberry', 'red', 'red-violet', 'rose', 'ruby', 'salmon', 'sapphire', 'scarlet', 'silver', 'slate-gray', 'spring-green', 'tan', 'teal', 'turquoise', 'ultramarine', 'violet', 'viridian', 'white', 'yellow']

class Unverified(BaseView):
    @ui.button(label="Verify With Roblox", style=discord.ButtonStyle.gray)
    async def verify(self, interaction: discord.Interaction[MatchMaker], _: discord.Button):
        await interaction.response.send_modal(GetRobloxUsername(interaction, False))
    
class GetRobloxUsername(BaseModal):
    name = ui.TextInput(
        label = "Roblox Name",
        placeholder = f"Type your roblox account name here",
        min_length = 3,
        max_length = 20
    )
    
    def __init__(self, interaction: discord.Interaction[MatchMaker], changing: bool):
        super().__init__("Roblox Verification", 120, interaction, Object(defer_ephemerally=True, thinking=True, get_user_data=True))
        
        self.changing = changing
        
    async def on_submit(self, interaction: discord.Interaction[MatchMaker]):
        name = self.name.value
        
        if not re.match(ROBLOX_NAME, name):
            return await interaction.followup.send(content="❌ **I could not find that roblox account")
            
        await interaction.edit_original_response("...")

class ManageAccount(commands.Cog):
    def __init__(self, bot: MatchMaker):
        self.bot: MatchMaker = bot
        
    @app_commands.command(
        name="account", 
        description="manage your settings & roblox account",
        extras = Object(defer_ephemerally=True, get_user_data=True)
    )
    async def account(self, interaction: discord.Interaction[MatchMaker]):
        data: User       = interaction.extras['users'][interaction.user.id]
        rblx: RobloxUser = await self.bot.roblox_client.get_user(data.roblox_id)
        
        if not rblx:
            return await interaction.followup.send(
                content = f"⚠️ **You are not verified**", 
                view    = Unverified(120, interaction, Object(get_user_data=True))
            )
            
        await interaction.followup.send(content=f"**{str(rblx)}**", ephemeral=True)
        
async def setup(bot: MatchMaker):
    cog = ManageAccount(bot)
    
    for command in cog.walk_app_commands():
        if hasattr(command, "callback"):
            setattr(command.callback, "__name__", f"{cog.qualified_name.lower()}_{command.callback.__name__}")
            setattr(command, "guild_only", False)
    
    await bot.add_cog(cog)