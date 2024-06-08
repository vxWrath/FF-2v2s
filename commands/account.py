from __future__ import annotations

import discord
import random
import re
import uuid

from discord import app_commands, ui
from discord.ext import commands
from typing import Literal

from resources import MatchMaker, Object, Extras, User, RobloxUser, BaseView, BaseModal, Colors, Region, NoRobloxUser, DeleteMessageView

ROBLOX_NAME = re.compile(r"^(?=^\w{3,20}$)[a-z0-9]+_?[a-z0-9]+$", flags=re.IGNORECASE)

word_bank = ['alice-blue', 'amaranth', 'amber', 'amethyst', 'apple-green', 'apple-red', 'apricot', 'aquamarine', 'azure', 'baby-blue', 'beige', 'brick-red', 'black', 'blue', 'blue-green', 'blue-violet', 'blush', 'bronze', 'brown', 'burgundy', 'carmine', 'cerise', 'cerulean', 'chocolate', 'cobalt-blue', 'coffee', 'copper', 'coral', 'crimson', 'cyan', 'desert-sand', 'electric-blue', 'emerald', 'gold', 'gray', 'green', 'indigo', 'ivory', 'jade', 'jungle-green', 'lavender', 'lemon', 'lilac', 'lime', 'magenta', 'maroon', 'navy-blue', 'olive', 'orange', 'orange-red', 'orchid', 'peach', 'pear', 'periwinkle', 'persian-blue', 'pink', 'plum', 'purple', 'raspberry', 'red', 'red-violet', 'rose', 'ruby', 'salmon', 'sapphire', 'scarlet', 'silver', 'slate-gray', 'spring-green', 'tan', 'teal', 'turquoise', 'ultramarine', 'violet', 'viridian', 'white', 'yellow']

class Unverified(BaseView):
    @ui.button(label="Verify With Roblox", style=discord.ButtonStyle.gray)
    async def verify(self, interaction: discord.Interaction[MatchMaker], _):
        await interaction.response.send_modal(GetRobloxUsername(interaction, self, True))
    
class GetRobloxUsername(BaseModal):
    name = ui.TextInput(
        label = "Roblox Name",
        placeholder = f"Type your roblox account name here",
        min_length = 3,
        max_length = 20
    )
    
    def __init__(self, interaction: discord.Interaction[MatchMaker], view, verifying: bool):
        super().__init__("Roblox Verification", 120, interaction)
        
        self.verifying = verifying
        self.view      = view
        
    async def on_submit(self, interaction: discord.Interaction[MatchMaker]):
        name = self.name.value
        
        if not re.match(ROBLOX_NAME, name):
            return await interaction.response.send_message(content="❌ **I could not find that roblox account", ephemeral=True)
        
        if self.verifying:
            await interaction.response.edit_message(content=f"🔎 *Searching...*", view=None, embed=None)
        else:
            await interaction.response.send_message(content=f"🔎 *Searching...*", ephemeral=True)
            
        rblx = await interaction.client.roblox_client.get_user_by_name(name)
            
        if not rblx:
            return await interaction.edit_original_response(content="❌ **I could not find that roblox account. Please restart.")

        if self.verifying:
            self.view.stop()
        else:
            self.view._refresh_timeout()
        
        avatars = await interaction.client.roblox_client.get_users_avatar([rblx.id])
        
        embed = discord.Embed(
            description = (
                f"## I have found the account, **[{rblx.name}]({rblx.profile_url})**. Is this correct?"
            ),
            color = Colors.blank
        )
        embed.set_thumbnail(url=avatars[rblx.id])
            
        await interaction.edit_original_response(content=None, embed=embed, view=VerifyRobloxAccount(interaction, self.view, self.verifying, rblx, avatars[rblx.id]))
        
class VerifyRobloxAccount(BaseView):
    def __init__(self, interaction: discord.Interaction[MatchMaker], view, verifying: bool, rblx: RobloxUser, avatar_url: str):
        super().__init__(120, interaction)
        
        self.verifying  = verifying
        self.view       = view
        self.rblx       = rblx
        self.avatar_url = avatar_url
        
    @ui.button(label="Yes, Continue", style=discord.ButtonStyle.green)
    async def yes(self, interaction: discord.Interaction[MatchMaker], _):
        self.stop()
        words = ' '.join(random.choices(word_bank, k=10))
        
        embed = discord.Embed(
            description = (
                f"## Verification Instructions\n"
                f"In order to verify that this is your account, you must put the following words in your **[account description]({self.rblx.profile_url})**:\n\n"
                f"`{words}`"
            ),
            color = Colors.blank
        )
        embed.set_thumbnail(url=self.avatar_url)
        
        if self.verifying:
            self.view.stop()
            view = self
        else:
            self.view._refresh_timeout()
            view = self.view
        
        await interaction.response.edit_message(embed=embed, view=CompleteVerification(interaction, view, self.verifying, self.rblx, self.avatar_url, words))
    
    @ui.button(label="No, Restart", style=discord.ButtonStyle.red)
    async def no(self, interaction: discord.Interaction[MatchMaker], _):
        if self.verifying:
            self.view.stop()
        else:
            self.view._refresh_timeout()
        
        await interaction.response.send_modal(GetRobloxUsername(interaction, self, self.verifying))
        
class CompleteVerification(BaseView):
    def __init__(self, interaction: discord.Interaction[MatchMaker], view, verifying: bool, rblx: RobloxUser, avatar_url: str, words: str):
        super().__init__(120, interaction, extras=Extras(custom_id=Object(
            done = Extras(defer_ephemerally=True, user_data=True)
        )))
        
        self.verifying  = verifying
        self.view       = view
        self.rblx       = rblx
        self.avatar_url = avatar_url
        self.words      = words
        
    @ui.button(label="Done", style=discord.ButtonStyle.green, custom_id=f"done:{uuid.uuid4()}")
    async def done(self, interaction: discord.Interaction[MatchMaker], _):
        message = await interaction.followup.send(content=f"🔎 *Getting info...*", ephemeral=True, wait=True)
        rblx    = await interaction.client.roblox_client.get_user(self.rblx.id)
        data    = interaction.extras['users'][interaction.user.id]

        if not rblx:
            raise NoRobloxUser(interaction.user)
        
        if self.words.lower() not in rblx.description.lower():
            return await message.edit(content="❌ **I couldn't find those words in your description**")
        
        embed = discord.Embed(
            description = f"## You have successfully verified with the account **[{rblx.name}]({rblx.profile_url})**!",
            color = Colors.blank
        )
        embed.set_thumbnail(url=self.avatar_url)
        
        await message.delete()
        await interaction.edit_original_response(embed=embed, view=None)
        
        data.roblox_id = rblx.id
        await interaction.client.database.update_user(data)
        
        self.stop()
        
        if self.verifying:
            self.view.stop()
        else:
            content = (
                f"## Account Settings\n"
                f"`Roblox Account:` **{rblx.name}** ({rblx.id})\n"
                f"`Match Making Region:` **{Region(data.settings.region).name}**\n\n"
                f"`Party Requests:` {'✅' if data.settings.party_requests else '❌'}\n"
                f"`Party Request Whitelist:` **{len(data.settings.party_request_whitelist)} members**\n"
                f"`Party Request Blacklist:` **{len(data.settings.party_request_blacklist)} members**\n"
            )
            
            await self.view.interaction.edit_original_response(content=content)
    
    @ui.button(label="Stop, Restart", style=discord.ButtonStyle.red)
    async def restart(self, interaction: discord.Interaction[MatchMaker], _):
        if self.verifying:
            self.view.stop()
        else:
            self.view._refresh_timeout()
        
        await interaction.response.send_modal(GetRobloxUsername(interaction, self.view, self.verifying))

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
        super().__init__(300, interaction)

        self.rblx = rblx

    @ui.select(cls=ui.Select, placeholder="Change Settings", options=[
        discord.SelectOption(label="Change roblox account", value="roblox"),
        discord.SelectOption(label="Change region", value="region"),
        discord.SelectOption(label="Change party request status", value="party_requests"),
        discord.SelectOption(label="View/Edit party request whitelist", value="whitelist"),
        discord.SelectOption(label="View/Edit party request blacklist", value="blacklist"),
    ])
    async def change_settings(self, interaction: discord.Interaction[MatchMaker], _):
        value = self.change_settings.values[0]
        if value == "roblox":
            return await interaction.response.send_modal(GetRobloxUsername(interaction, self, False))
        elif value == "region":
            return await interaction.response.send_message(content="**Select a new match making region below**", view=SelectRegion(interaction, self, self.rblx), ephemeral=True)
        elif value == "party_requests":
            view = FlipQueueRequestStatus(interaction, self, self.rblx)
            return await interaction.response.send_message(content=view.content, view=view, ephemeral=True)
        elif value == "whitelist" or value == "blacklist":
            self.stop()

            view = PartyRequestList(interaction, self, self.rblx, value)
            return await interaction.response.edit_message(content=None, embed=view.format_embed(), view=view)

class ManageAccount(commands.Cog):
    def __init__(self, bot: MatchMaker):
        self.bot: MatchMaker = bot
        
    @app_commands.command(
        name="account", 
        description="manage your settings & roblox account",
        extras=Extras(defer_ephemerally=True, user_data=True), # type: ignore
    )
    async def account(self, interaction: discord.Interaction[MatchMaker]):
        data = interaction.extras['users'][interaction.user.id]
        rblx = await self.bot.roblox_client.get_user(data.roblox_id)
        
        if not rblx:
            return await interaction.followup.send(
                content = f"⚠️ **You are not verified**", 
                view    = Unverified(120, interaction)
            )
            
        content = (
            f"## Account Settings\n"
            f"`Roblox Account:` **{rblx.name}** ({rblx.id})\n"
            f"`Match Making Region:` **{Region(data.settings.region).name}**\n\n"
            f"`Party Requests:` {'✅' if data.settings.party_requests else '❌'}\n"
            f"`Party Request Whitelist:` **{len(data.settings.party_request_whitelist)} members**\n"
            f"`Party Request Blacklist:` **{len(data.settings.party_request_blacklist)} members**\n"
        )
            
        await interaction.followup.send(content=content, view=ChangeAccountSettings(interaction, rblx))
        
async def setup(bot: MatchMaker):
    cog = ManageAccount(bot)
    
    for command in cog.walk_app_commands():
        if hasattr(command, "callback"):
            setattr(command.callback, "__name__", f"{cog.qualified_name.lower()}_{command.callback.__name__}")
            setattr(command, "guild_only", False)
    
    await bot.add_cog(cog)