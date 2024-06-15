from typing import Any, Optional, List

import discord
import io
import json
import numpy
from colorthief import ColorThief
from discord.ext.commands import Bot as MatchMaker
from discord import ui

from .exceptions import CheckFailure
from .models import Extras, Match, Region, CheckFailureType
from .config import Config

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

class DeleteMessageView(BaseView):
    def __init__(self, interaction: discord.Interaction[MatchMaker], timeout: float):
        super().__init__(timeout, interaction, extras=Extras(defer=True))

    @ui.button(label="Delete Message", emoji="🗑", style=discord.ButtonStyle.gray)
    async def delete(self, interaction: discord.Interaction[MatchMaker], _):
        self.stop()
        await interaction.delete_original_response()

    async def on_timeout(self) -> None:
        if not self.interaction:
            return

        try:
            await self.interaction.delete_original_response()
        except discord.HTTPException:
            pass

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
        
    @staticmethod
    def ensure_color(color: discord.Color) -> discord.Color:
        return color if color.value else Colors.blank

def _format_bot_message(message: discord.Message, prev: bool=False) -> str:
    if message.embeds:
        desc = message.embeds[0].description or 'No Description'
        desc = discord.utils.remove_markdown(desc).strip().replace('\n', '\n\t')

        return f"Embed:\n\t{desc}\n"
    else:
        return f"{discord.utils.remove_markdown(message.clean_content)}"

async def send_thread_log(matchup: Match, thread: discord.Thread) -> int:
    config = Config.get()
    thread_log = thread.guild.get_channel(config.THREAD_LOG)
    
    previous_author = None

    content  = f"THREAD ID - {thread.id} | MATCH ID: {matchup.id}"
    messages = "THREAD START\n"
    i        = 1
    
    async for message in thread.history(limit=250, oldest_first=True):
        if message.author.bot:
            if previous_author == message.author:
                messages += f"{i}) {_format_bot_message(message, prev=True)}\n"
            else:
                messages += f"\n{message.author.name} ({message.author.id}) @ {message.created_at.strftime('%m/%d/%Y %r')}\n{i}) {_format_bot_message(message)}\n"
        else:
            if previous_author == message.author:
                messages += f"{i}) {discord.utils.remove_markdown(message.clean_content)}\n"
            else:
                messages += f"\n{message.author.name} ({message.author.id}) @ {message.created_at.strftime('%m/%d/%Y %r')}\n{i}) {discord.utils.remove_markdown(message.clean_content)}\n"
                
        i += 1
        previous_author = message.author
    
    f = discord.File(io.StringIO(messages.strip()), filename="messages.txt")
    msg = await thread_log.send(content=content, file=f)

    return msg.id

async def log_score(bot: MatchMaker, matchup: Match, voters: List[int], forced: Optional[bool]=False):
    embed = discord.Embed(
        description = (
            f"# 2v2 Result\n"
            f"`{matchup.team_one.score or 'NA':>2}` **- <@{matchup.team_one.player_one}> & <@{matchup.team_one.player_two}>** (🏆 {matchup.team_one.trophies})\n"
            f"`{matchup.team_two.score or 'NA':>2}` **- <@{matchup.team_two.player_one}> & <@{matchup.team_two.player_two}>** (🏆 {matchup.team_two.trophies})\n\n"
            f"`Region:` **{Region(matchup.region).name}**\n"
            f"`Started:` {discord.utils.format_dt(matchup.created_at, "f")}\n\n"
        ),
        color = Colors.blank,
        timestamp = discord.utils.utcnow(),
    )
    embed.set_footer(text=f"ID: {matchup.id}")

    if forced:
        embed.set_author(name="This matchup result was FORCED")

    if voters:
        embed.description += f"`Voters:` *" + ", ".join([f"<@{x}>" for x in voters]) + "*\n\n"

    config = Config.get()

    guild = bot.get_guild(config.MAIN_GUILD)
    score_log = guild.get_channel(config.SCORE_LOG)

    await score_log.send(
        content = f"<@{matchup.team_one.player_one}> <@{matchup.team_one.player_two}> <@{matchup.team_two.player_one}> <@{matchup.team_two.player_two}>",
        embed = embed
    )
        
def trophy_change(your_team, opponent_team) -> int:
    base_change = 37.5
    is_win      = your_team.score > opponent_team.score

    trophy_factor = (opponent_team.trophies - your_team.trophies) / 100
    score_factor  = (your_team.score - opponent_team.score) / 5

    if is_win:
        return int(numpy.clip(base_change + trophy_factor * 10 + score_factor, 10, 50))
    else:
        return int(numpy.clip(-base_change + trophy_factor * 10 + score_factor, -50, -10))
    
def staff_only():
    async def pred(interaction: discord.Interaction[MatchMaker]) -> True:
        config = Config.get()

        if interaction.user.id in config['ADMINS'] + config['DEVELOPERS'] or interaction.user.get_role(config['STAFF_ROLE']):
            return True
        raise CheckFailure(CheckFailureType.staff)
        
    return discord.app_commands.check(pred)

def admin_only():
    async def pred(interaction: discord.Interaction[MatchMaker]) -> True:
        config = Config.get()
        
        if interaction.user.id in config['ADMINS'] + config['DEVELOPERS']:
            return True
        raise CheckFailure(CheckFailureType.admin)
        
    return discord.app_commands.check(pred)

async def setup(bot: MatchMaker):
    pass