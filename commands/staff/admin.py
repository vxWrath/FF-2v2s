import discord

from discord import app_commands, ui
from discord.ext import commands
from typing import List, Dict, Any

from resources import MatchMaker, Extras, Colors, admin_only, Config, BaseView
from ..events import Play

settings = {
    "STAFF_ROLE": {"cls": ui.RoleSelect, "name": "Staff Role"},

    "THREAD_CHANNEL": {"cls": ui.ChannelSelect, "name": "Match Thread Channel"},
    "THREAD_LOG": {"cls": ui.ChannelSelect, "name": "Match Log Channel"},
    "SCORE_LOG": {"cls": ui.ChannelSelect, "name": "Score Log Channel"},
    "BAN_LOG": {"cls": ui.ChannelSelect, "name": "Ban Log Channel"},

    "PANEL_CHANNEL": {"cls": ui.ChannelSelect, "name": "Panel Channel"},
}

async def setting_autocomplete(interaction: discord.Interaction[MatchMaker], current: str) -> List[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=data['name'], value=data['name'])
        for config, data in settings.items()
        if current.lower() in data['name'].lower()
    ]

class ChangeSetting(BaseView):
    def __init__(self, interaction: discord.Interaction[MatchMaker], config: str, setting: Dict[str, Any]):
        super().__init__(120, interaction)

        self.config  = config
        self.setting = setting

        self.select: ui.RoleSelect | ui.ChannelSelect = setting['cls'](placeholder="Options")
        self.select.callback = self.callback

        self.add_item(self.select)

    async def callback(self, interaction: discord.Interaction[MatchMaker]):
        await interaction.response.send_message(
            content = f"✅ `{self.setting['name'].lower()}` **has been set to** {self.select.values[0].mention}",
            allowed_mentions = discord.AllowedMentions(roles=False)
        )

        config = Config.get()
        config[self.config] = self.select.values[0].id
        
        Config.update()

@app_commands.guild_only()
class Admin(commands.GroupCog, name="admin", description="admin commands"):
    def __init__(self, bot: MatchMaker):
        self.bot = bot

    @app_commands.command(
        name="sendpanel", 
        description="send the play panel",
        extras=Extras(defer_ephemerally=True, user_data=True),
    )
    @admin_only()
    async def sendpanel(self, interaction: discord.Interaction[MatchMaker]):
        config = Config.get()
        cog    = interaction.client.get_cog('Events')

        channel = self.bot.get_partial_messageable(config.PANEL_CHANNEL, guild_id=config.MAIN_GUILD, type=discord.ChannelType.text)

        embed = discord.Embed(
            description = (
                f"## Play a 2v2\n"
                f"`Queueing:` **{cog.counts['queueing']}**\n"
                f"` Playing:` **{cog.counts['playing']}**\n\n"
            ),
            color = Colors.white
        )
        embed.set_thumbnail(url=interaction.client.user.display_avatar)
        embed.set_author(name=interaction.client.user.name, icon_url=interaction.client.user.display_avatar)
        embed.set_footer(text="Click play to join the queue or use /play")

        view    = Play()
        message = await channel.send(embed=embed, view=view)

        self.bot.add_view(view, message_id=message.id)

        config.PANEL_MESSAGE = message.id
        Config.update()

        await interaction.followup.send(f"Sent - {message.jump_url}")

    @app_commands.command(
        name="view", 
        description="view the configuration",
        extras=Extras()
    )
    @admin_only()
    async def view_config(self, interaction: discord.Interaction[MatchMaker]):
        config  = Config.get()
        content = "## Config\n"

        for key, value in config.items():
            if (setting := settings.get(key)):
                if 'ROLE' in key:
                    role     = interaction.guild.get_role(value)
                    content += f"`{setting['name']}:` {role.mention}\n"
                else:
                    channel  = interaction.guild.get_channel_or_thread(value)
                    content += f"`{setting['name']}:` {channel.mention}\n"

                continue

            if key == "PANEL_MESSAGE":
                channel = interaction.guild.get_channel(config.PANEL_CHANNEL)
                message = channel.get_partial_message(value)

                content += f"`Panel Message:` {message.jump_url}\n"

        await interaction.response.send_message(content=content, ephemeral=True, allowed_mentions=discord.AllowedMentions.none())

    @app_commands.command(
        name="set", 
        description="set different settings",
        extras=Extras()
    )
    @app_commands.describe(setting="the setting to set")
    @app_commands.autocomplete(setting=setting_autocomplete)
    @admin_only()
    async def set_config(self, interaction: discord.Interaction[MatchMaker], setting: str):
        result = [(config, data) for config, data in settings.items() if setting.lower() in data['name'].lower()]

        if not result:
            await interaction.response.send_message(content=f"❌ **That is not a setting**", ephemeral=True)

        config, setting = result[0]
        
        view = ChangeSetting(interaction, config, setting)
        
        await interaction.response.send_message(
            content = f"**Select an option to below to set as the new** `{setting['name'].lower()}`",
            view = view,
            ephemeral = True
        )

    @app_commands.command(
        name="set", 
        description="set different settings",
        extras=Extras()
    )
    @app_commands.describe(setting="the setting to set")
    @app_commands.autocomplete(setting=setting_autocomplete)
    @admin_only()
    async def set_config(self, interaction: discord.Interaction[MatchMaker], setting: str):
        result = [(config, data) for config, data in settings.items() if setting.lower() in data['name'].lower()]

        if not result:
            await interaction.response.send_message(content=f"❌ **That is not a setting**", ephemeral=True)

        config, setting = result[0]
        
        view = ChangeSetting(interaction, config, setting)
        
        await interaction.response.send_message(
            content = f"**Select an option to below to set as the new** `{setting['name'].lower()}`",
            view = view,
            ephemeral = True
        )

    @app_commands.command(
        name="set", 
        description="set different settings",
        extras=Extras()
    )
    @app_commands.describe(setting="the setting to set")
    @app_commands.autocomplete(setting=setting_autocomplete)
    @admin_only()
    async def set_config(self, interaction: discord.Interaction[MatchMaker], setting: str):
        result = [(config, data) for config, data in settings.items() if setting.lower() in data['name'].lower()]

        if not result:
            await interaction.response.send_message(content=f"❌ **That is not a setting**", ephemeral=True)

        config, setting = result[0]
        
        view = ChangeSetting(interaction, config, setting)
        
        await interaction.response.send_message(
            content = f"**Select an option to below to set as the new** `{setting['name'].lower()}`",
            view = view,
            ephemeral = True
        )
        
async def setup(bot: MatchMaker):
    cog = Admin(bot)
    
    for command in cog.walk_app_commands():
        if hasattr(command, "callback"):
            setattr(command.callback, "__name__", f"{cog.qualified_name.lower()}_{command.callback.__name__}")
            setattr(command, "guild_only", False)
    
    await bot.add_cog(cog)