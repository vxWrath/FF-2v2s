import discord

from discord import app_commands, ui
from discord.ext import commands
from typing import List

from resources import MatchMaker, Extras, Colors, admin_only, Config
from ..events import Play

class Panel(commands.Cog):
    def __init__(self, bot: MatchMaker):
        self.bot: MatchMaker = bot

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
        
async def setup(bot: MatchMaker):
    cog = Panel(bot)
    
    for command in cog.walk_app_commands():
        if hasattr(command, "callback"):
            setattr(command.callback, "__name__", f"{cog.qualified_name.lower()}_{command.callback.__name__}")
            setattr(command, "guild_only", False)
    
    await bot.add_cog(cog)