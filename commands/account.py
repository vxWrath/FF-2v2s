import discord
import random
import re
import uuid

from discord import app_commands, ui
from discord.ext import commands

from resources import MatchMaker, Object, Extras, User, RobloxUser, BaseView, BaseModal, Colors, Region

ROBLOX_NAME = re.compile(r"^(?=^\w{3,20}$)[a-z0-9]+_?[a-z0-9]+$", flags=re.IGNORECASE)

word_bank = ['alice-blue', 'amaranth', 'amber', 'amethyst', 'apple-green', 'apple-red', 'apricot', 'aquamarine', 'azure', 'baby-blue', 'beige', 'brick-red', 'black', 'blue', 'blue-green', 'blue-violet', 'blush', 'bronze', 'brown', 'burgundy', 'carmine', 'cerise', 'cerulean', 'chocolate', 'cobalt-blue', 'coffee', 'copper', 'coral', 'crimson', 'cyan', 'desert-sand', 'electric-blue', 'emerald', 'gold', 'gray', 'green', 'indigo', 'ivory', 'jade', 'jungle-green', 'lavender', 'lemon', 'lilac', 'lime', 'magenta', 'maroon', 'navy-blue', 'olive', 'orange', 'orange-red', 'orchid', 'peach', 'pear', 'periwinkle', 'persian-blue', 'pink', 'plum', 'purple', 'raspberry', 'red', 'red-violet', 'rose', 'ruby', 'salmon', 'sapphire', 'scarlet', 'silver', 'slate-gray', 'spring-green', 'tan', 'teal', 'turquoise', 'ultramarine', 'violet', 'viridian', 'white', 'yellow']

class Unverified(BaseView):
    @ui.button(label="Verify With Roblox", style=discord.ButtonStyle.gray)
    async def verify(self, interaction: discord.Interaction[MatchMaker], _: discord.Button):
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
    async def yes(self, interaction: discord.Interaction[MatchMaker], _: discord.Button):
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
    async def no(self, interaction: discord.Interaction[MatchMaker], _: discord.Button):
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
    async def done(self, interaction: discord.Interaction[MatchMaker], _: discord.Button):
        message = await interaction.followup.send(content=f"🔎 *Getting info...*", ephemeral=True, wait=True)
        rblx    = await interaction.client.roblox_client.get_user(self.rblx.id)
        data    = interaction.extras['users'][interaction.user.id]
        
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
        await interaction.client.database.update_user(data, ["roblox_id"])
        
        self.stop()
        
        if self.verifying:
            self.view.stop()
        else:
            content = (
                f"## Account Settings\n"
                f"`Match Making Region:` **{Region(data.region).name}**\n"
                f"`Roblox Account:` **{rblx.name}** ({rblx.id})\n"
            )
            
            await self.view.interaction.edit_original_response(content=content)
    
    @ui.button(label="Stop, Restart", style=discord.ButtonStyle.red)
    async def restart(self, interaction: discord.Interaction[MatchMaker], _: discord.Button):
        if self.verifying:
            self.view.stop()
        else:
            self.view._refresh_timeout()
        
        await interaction.response.send_modal(GetRobloxUsername(interaction, self.view, self.verifying))

class ChangeAccountSettings(BaseView):
    @ui.select(cls=ui.Select, placeholder="Change Settings", options=[
        discord.SelectOption(label="Change roblox account", value="roblox"),
        discord.SelectOption(label="Change region", value="region"),
        discord.SelectOption(label="Change queue request status", value="queue"),
        discord.SelectOption(label="View/Edit queue request whitelist", value="whitelist"),
        discord.SelectOption(label="View/Edit queue request blacklist", value="blacklist"),
    ])
    async def change_settings(self, interaction: discord.Interaction[MatchMaker], _: discord.SelectMenu):
        if self.change_settings.values[0] == "roblox":
            return await interaction.response.send_modal(GetRobloxUsername(interaction, self, False))
        
        await interaction.response.send_message(content="*Not Done*", ephemeral=True)

class ManageAccount(commands.Cog):
    def __init__(self, bot: MatchMaker):
        self.bot: MatchMaker = bot
        
    @app_commands.command(
        name="account", 
        description="manage your settings & roblox account",
        extras=Extras(defer_ephemerally=True, user_data=True),
    )
    async def account(self, interaction: discord.Interaction[MatchMaker]):
        data: User       = interaction.extras['users'][interaction.user.id]
        rblx: RobloxUser = await self.bot.roblox_client.get_user(data.roblox_id)
        
        if not rblx:
            return await interaction.followup.send(
                content = f"⚠️ **You are not verified**", 
                view    = Unverified(120, interaction)
            )
            
        content = (
            f"## Account Settings\n"
            f"`Roblox Account:` **{rblx.name}** ({rblx.id})\n"
            f"`Match Making Region:` **{Region(data.settings.region).name}**\n\n"
            f"`Queue Requests:` {'✅' if data.settings.queue_requests else '❌'}\n"
            f"`Queue Request Whitelist:` **{len(data.settings.queue_request_whitelist)} members**\n"
            f"`Queue Request Blacklist:` **{len(data.settings.queue_request_blacklist)} members**\n"
        )
            
        await interaction.followup.send(content=content, view=ChangeAccountSettings(300, interaction), suppress_embeds=True)
        
async def setup(bot: MatchMaker):
    cog = ManageAccount(bot)
    
    for command in cog.walk_app_commands():
        if hasattr(command, "callback"):
            setattr(command.callback, "__name__", f"{cog.qualified_name.lower()}_{command.callback.__name__}")
            setattr(command, "guild_only", False)
    
    await bot.add_cog(cog)