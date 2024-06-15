from __future__ import annotations

import discord
import random
import re
import uuid

from discord import app_commands, ui
from discord.ext import commands
from typing import Literal

from resources import MatchMaker, Object, Extras, User, RobloxUser, BaseView, BaseModal, Colors, Region, DeleteMessageView

class SelectRegion(BaseView):
    def __init__(self, interaction: discord.Interaction[MatchMaker], view, rblx: RobloxUser):
        super().__init__(120, interaction, extras=Extras(defer_ephemerally=True, user_data=True))

        self.view = view
        self.rblx = rblx

        for region in Region.__members__.values():
            self.regions.add_option(label=region.name, value=str(region.value))

    @ui.select(cls=ui.Select, placeholder="Regions", options=[])
    async def regions(self, interaction: discord.Interaction[MatchMaker], _):
        await interaction.edit_original_response(content="✅ **Region Updated**", view=None)
        
        data: User = interaction.extras['users'][interaction.user.id]
        data.settings.region = int(self.regions.values[0])
        await interaction.client.database.update_user(data)
        
        self.stop()
        
        content = (
            f"## Account Settings\n"
            f"`Roblox Account:` **{self.rblx.name}** ({self.rblx.id})\n"
            f"`Match Making Region:` **{Region(data.settings.region).name}**\n\n"
            f"`Party Requests:` {'✅' if data.settings.party_requests else '❌'}\n"
            f"`Party Request Whitelist:` **{len(data.settings.party_request_whitelist)} members**\n"
            f"`Party Request Blacklist:` **{len(data.settings.party_request_blacklist)} members**\n"
        )
        
        await self.view.interaction.edit_original_response(content=content)

class FlipQueueRequestStatus(BaseView):
    def __init__(self, interaction: discord.Interaction[MatchMaker], view: ChangeAccountSettings, rblx: RobloxUser):
        super().__init__(120, interaction, extras=Extras(defer_ephemerally=True, user_data=True))

        self.view = view
        self.rblx = rblx

        data: User = view.interaction.extras['users'][interaction.user.id]

        if data.settings.party_requests:
            self.content = f"Do you want to turn party requests **off**?"
            self.onoff.style = discord.ButtonStyle.red
        else:
            self.content = f"Do you want to turn party requests **on**?"
            self.onoff.style = discord.ButtonStyle.green

    @ui.button(label="Yes")
    async def onoff(self, interaction: discord.Interaction[MatchMaker], _):
        data: User = interaction.extras['users'][interaction.user.id]

        if data.settings.party_requests:
            await interaction.edit_original_response(content="✅ Party requests turned **off**", view=None)
        else:
            await interaction.edit_original_response(content="✅ Party requests turned **on**", view=None)
        
        data.settings.party_requests = not data.settings.party_requests
        await interaction.client.database.update_user(data)
        
        self.stop()
        
        content = (
            f"## Account Settings\n"
            f"`Roblox Account:` **{self.rblx.name}** ({self.rblx.id})\n"
            f"`Match Making Region:` **{Region(data.settings.region).name}**\n\n"
            f"`Party Requests:` {'✅' if data.settings.party_requests else '❌'}\n"
            f"`Party Request Whitelist:` **{len(data.settings.party_request_whitelist)} members**\n"
            f"`Party Request Blacklist:` **{len(data.settings.party_request_blacklist)} members**\n"
        )
        
        self.view.interaction.extras['users'][interaction.user.id] = data
        await self.view.interaction.edit_original_response(content=content)

class PartyRequestList(BaseView):
    def __init__(self, interaction: discord.Interaction[MatchMaker], view: ChangeAccountSettings, rblx: RobloxUser, list_type: Literal['whitelist', 'blacklist']):
        super().__init__(300, interaction, extras=Extras(defer_ephemerally=True, user_data=True))

        self.view = view
        self.rblx = rblx
        self.list_type = list_type
        
        self.members.max_values = min(interaction.guild.member_count, 25)
        self.members.default_values = [
            discord.SelectDefaultValue(id=member_id, type=discord.SelectDefaultValueType.user) 
            for member_id in view.interaction.extras['users'][interaction.user.id].settings[f'party_request_{list_type}']
        ]

    def format_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title = f"{self.list_type.title()}ed Members",
            color = Colors.blank,
            timestamp = discord.utils.utcnow()
        )

        if self.list_type == "whitelist":
            embed.description = f"If you have party requests off, this will allow the following users to still send party requests to you.\n\n"
        else:
            embed.description = f"If you have party requests on, this will prohibit the following users from sending you party requests.\n\n"

        for dv in self.members.default_values:
            embed.description += f"<@{dv.id}>\n"

        return embed

    @ui.select(cls=ui.UserSelect, placeholder="Members", min_values=0)
    async def members(self, interaction: discord.Interaction[MatchMaker], _):
        data: User = interaction.extras['users'][interaction.user.id]

        self.members.default_values = [discord.SelectDefaultValue.from_user(user) for user in self.members.values]
        data.settings[f'party_request_{self.list_type}'] = [x.id for x in self.members.values]

        await interaction.edit_original_response(embed=self.format_embed(), view=self)
        await interaction.client.database.update_user(data)

class ChangeAccountSettings(BaseView):
    def __init__(self, interaction: discord.Interaction[MatchMaker], rblx: RobloxUser):
        super().__init__(300, interaction, Extras(defer=True, user_data=True))

        self.rblx = rblx

    @ui.select(cls=ui.Select, placeholder="Change Settings", options=[
        discord.SelectOption(label="Update roblox account", value="roblox"),
        discord.SelectOption(label="Change region", value="region"),
        discord.SelectOption(label="Change party request status", value="party_requests"),
        discord.SelectOption(label="View/Edit party request whitelist", value="whitelist"),
        discord.SelectOption(label="View/Edit party request blacklist", value="blacklist"),
    ])
    async def change_settings(self, interaction: discord.Interaction[MatchMaker], _):
        value = self.change_settings.values[0]

        if value == "roblox":
            data    = interaction.extras['users'][interaction.user.id]
            rblx_id = await interaction.client.roblox_client.retreive_from_bloxlink(interaction.user.id)

            if not rblx_id:
                return await interaction.followup.send(content=f"❌ **You shouldn't be here**", ephemeral=True)
            
            if rblx_id == self.rblx.id:
                return await interaction.followup.send(content=(
                    f"❌ **You need to update your account through bloxlink**"
                ))
            
            await interaction.edit_original_response(content=f"✅ **Automatically updated.**", view=None)

            data.roblox_id = rblx_id
            return await interaction.client.database.update_user(data)

        elif value == "region":
            return await interaction.followup.send(content="**Select a new match making region below**", view=SelectRegion(interaction, self, self.rblx), ephemeral=True)
        elif value == "party_requests":
            view = FlipQueueRequestStatus(interaction, self, self.rblx)
            return await interaction.followup.send(content=view.content, view=view, ephemeral=True)
        elif value == "whitelist" or value == "blacklist":
            self.stop()

            view = PartyRequestList(interaction, self, self.rblx, value)
            return await interaction.edit_original_response(content=None, embed=view.format_embed(), view=view)

class ManageAccount(commands.Cog):
    def __init__(self, bot: MatchMaker):
        self.bot: MatchMaker = bot
        
    @app_commands.command(
        name="account", 
        description="manage your settings & roblox account",
        extras=Extras(defer_ephemerally=True, user_data=True),
    )
    async def account(self, interaction: discord.Interaction[MatchMaker]):
        data = interaction.extras['users'][interaction.user.id]
        rblx = await self.bot.roblox_client.get_user(data.roblox_id)
        
        if not rblx:
            rblx_id = await self.bot.roblox_client.retreive_from_bloxlink(interaction.user.id)

            if not rblx_id:
                return await interaction.followup.send(content=(
                    f"❌ **You are not verified with <@426537812993638400>. Once you are verified (`/verify`), run this command again.**"
                ))
            
            await interaction.followup.send(content=(
                f"✅ **You have been automatically verified. Run this command again if you want to view or manage your settings.**"
            ))

            data.roblox_id = rblx_id
            return await interaction.client.database.update_user(data)

        content = (
            f"## Account Settings\n"
            f"`Roblox Account:` **{rblx.name}** ({rblx.id})\n"
            f"`Match Making Region:` **{Region(data.settings.region).name}**\n\n"
            f"`Party Requests:` {'✅' if data.settings.party_requests else '❌'}\n"
            f"`Party Request Whitelist:` **{len(data.settings.party_request_whitelist)} members**\n"
            f"`Party Request Blacklist:` **{len(data.settings.party_request_blacklist)} members**\n"
        )
            
        await interaction.followup.send(content=content, view=ChangeAccountSettings(interaction, rblx))

    @app_commands.command(
        name="settings", 
        description="manage your settings & roblox account",
        extras=Extras(defer_ephemerally=True, user_data=True),
    )
    async def settings(self, interaction: discord.Interaction[MatchMaker]):
        await self.account.callback(self, interaction)
        
async def setup(bot: MatchMaker):
    cog = ManageAccount(bot)
    
    for command in cog.walk_app_commands():
        if hasattr(command, "callback"):
            setattr(command.callback, "__name__", f"{cog.qualified_name.lower()}_{command.callback.__name__}")
            setattr(command, "guild_only", False)
    
    await bot.add_cog(cog)