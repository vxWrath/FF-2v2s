import asyncio
import datetime
import discord

from discord import app_commands, ui
from discord.ext import commands

from resources import MatchMaker, Extras, Colors, THREAD_CHANNEL

def is_thread(interaction: discord.Interaction) -> bool:
    return interaction.channel.type == discord.ChannelType.private_thread and interaction.channel.parent.id == THREAD_CHANNEL

class Result(commands.Cog):
    def __init__(self, bot: MatchMaker):
        self.bot: MatchMaker = bot

    @app_commands.command(
        name="result", 
        description="report the score & stats of a matchup",
        extras = Extras(defer_ephemerally=True, user_data=True)
    )
    @app_commands.describe(your_score="your team's score", opponents_score="your opponent's score")
    @app_commands.rename(your_score="your-score", opponents_score="opponents-score")
    @app_commands.check(is_thread)
    async def result(self, interaction: discord.Interaction[MatchMaker], 
        your_score: app_commands.Range[int, 0, 100], 
        opponents_score: app_commands.Range[int, 0, 100]
    ):
        data = interaction.extras['users'][interaction.user.id]
        rblx = await self.bot.roblox_client.get_user(data.roblox_id)
        
        if not rblx:
            return await interaction.followup.send(content=f"⚠️ **You are not verified. Run /account to verify**")
        
        matchup = await interaction.client.database.get_match_by_thread(interaction.channel.id)
        
        yours    = matchup.team_one if interaction.user.id in [matchup.team_one.player_one, matchup.team_one.player_two] else matchup.team_two
        opponent = matchup.team_two if yours == matchup.team_one else matchup.team_one
        
        is_team_one = yours == matchup.team_one
        
        if is_team_one:
            await interaction.followup.send(content=(
                f"`{your_score:>2}` **- <@{yours.player_one}> & <@{yours.player_two}>**\n"
                f"`{opponents_score:>2}` **- <@{opponent.player_one}> & <@{opponent.player_two}>**"
            ))
        else:
            await interaction.followup.send(content=(
                f"`{opponents_score:>2}` - **<@{opponent.player_one}> & <@{opponent.player_two}>**\n"
                f"`{your_score:>2}` - **<@{yours.player_one}> & <@{yours.player_two}>**"
            ))
        
async def setup(bot: MatchMaker):
    cog = Result(bot)
    
    for command in cog.walk_app_commands():
        if hasattr(command, "callback"):
            setattr(command.callback, "__name__", f"{cog.qualified_name.lower()}_{command.callback.__name__}")
            setattr(command, "guild_only", True)
    
    await bot.add_cog(cog)