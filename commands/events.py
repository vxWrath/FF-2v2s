import discord
import asyncio

from discord.ext import commands
from discord import ui
from resources import MatchMaker, Colors, Extras, BaseView, Config, Unverified
from typing import Optional

from .play import LinkOrSkip, FOOTBALL_FUSION_LINK

class Play(BaseView):
    def __init__(self):
        super().__init__(None, extras=Extras(defer=True, user_data=True))

    @ui.select(cls=ui.Select, placeholder="Click here to find 2v2s", custom_id="play", min_values=0, options=[
        discord.SelectOption(label="Create Party")
    ])
    async def play(self, interaction: discord.Interaction[MatchMaker], _):
        data = interaction.extras['users'][interaction.user.id]
        rblx = await interaction.client.roblox_client.get_user(data.roblox_id)
        
        if not rblx:
            raise Unverified(interaction.user)
        
        if interaction.client.states[interaction.user.id]:
            return await interaction.followup.send(content=f"❌ **You can't play because you {interaction.client.states[interaction.user.id].message}**", ephemeral=True)
        
        embed = discord.Embed(
            description = f"**If you have an active private server for [Football Fusion 2]({FOOTBALL_FUSION_LINK}), provide the link below.**",
            color = Colors.blank
        )
        embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)

        await interaction.followup.send(
            embed = embed,
            view  = LinkOrSkip(None, "one", data, rblx),
            ephemeral = True
        )

    async def on_timeout(self) -> None:
        return
    
    async def check_func(self, interaction: discord.Interaction[MatchMaker]):
        return True

class Events(commands.Cog):
    def __init__(self, bot: MatchMaker):
        self.bot      = bot
        self.batching = False
        self.task     = None

        self.counts = {
            None: 0,
            "playing": 0,
            "queueing": 0,
        }

    def add_view(self):
        view   = Play()
        config = Config.get()

        self.bot.add_view(view, message_id=config.PANEL_MESSAGE)

    @commands.Cog.listener(name="on_player_state_update")
    async def player_state_update(self, before: Optional[str], after: Optional[str]):
        self.counts[before] -= 1
        self.counts[after]  += 1

        if self.batching:
            return
        
        self.batching = True
        await asyncio.sleep(15)
        self.batching = False

        config = Config.get()

        channel = self.bot.get_partial_messageable(config.PANEL_CHANNEL, guild_id=config.MAIN_GUILD, type=discord.ChannelType.text)
        message = channel.get_partial_message(config.PANEL_MESSAGE)

        embed = discord.Embed(
            description = (
                f"## Find 2v2s\n"
                f"`Queueing:` **{self.counts['queueing']}**\n"
                f"` Playing:` **{self.counts['playing']}**\n\n"
            ),
            color = Colors.white
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar)
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.display_avatar)
        embed.set_footer(text="Click play to join the queue or use /play")

        try:
            await message.edit(embed=embed)
        except discord.errors.NotFound:
            view    = Play()
            message = await channel.send(embed=embed, view=view)

            self.bot.add_view(view, message_id=message.id)

            config.PANEL_MESSAGE = message.id
            Config.update()

async def setup(bot: MatchMaker):
    await bot.add_cog(Events(bot))