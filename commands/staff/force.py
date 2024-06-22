import asyncio
import datetime
import discord
import collections
import numpy

from discord import app_commands
from discord.ext import commands

from resources import MatchMaker, Extras, staff_only, Config, send_thread_log, is_admin

@app_commands.guild_only()
class ForceResult(commands.GroupCog, name="force", description="force cancel or force result of a match"):
    def __init__(self, bot: MatchMaker):
        self.bot = bot

    @app_commands.command(
        name="cancel", 
        description="forcefully cancel a match",
        extras=Extras(defer=True),
    )
    @app_commands.rename(match_id="match-id")
    @staff_only()
    async def force_cancel(self, interaction: discord.Interaction[MatchMaker], match_id: str):
        matchup = await interaction.client.database.get_match(match_id)

        if not matchup:
            return await interaction.followup.send(content="❌ **I couldn't find a match with that ID**")
        
        if not is_admin(interaction.user) and interaction.user.id in [matchup.team_one.player_one, matchup.team_one.player_two, matchup.team_two.player_one, matchup.team_two.player_two]:
            return await interaction.followup.send(content="❌ **You can't forcibly cancel one of your own matches**")

        await interaction.followup.send(content = f"**Match ID `{match_id}` has been forcibly canceled. Deleting it {discord.utils.format_dt(discord.utils.utcnow() + datetime.timedelta(seconds=60), "R")}**",)
        interaction.client.loop.create_task(send_thread_log(matchup, interaction.channel))

        interaction.client.states.remove([
            matchup.team_one.player_one, 
            matchup.team_one.player_two, 
            matchup.team_two.player_one,
            matchup.team_two.player_two
        ])
        
        if matchup.thread and (thread := interaction.guild.get_thread(matchup.thread)):
            interaction.client.loop.create_task(send_thread_log(matchup, thread))

            await asyncio.sleep(60)
            await thread.delete()
        else:
            await asyncio.sleep(60)

        await interaction.client.database.delete_match(matchup)

    @app_commands.command(
        name="result", 
        description="forcefully set the result of a match",
        extras=Extras(defer_ephemerally=True),
    )
    @app_commands.rename(match_id="match-id")
    @staff_only()
    async def force_result(self, interaction: discord.Interaction[MatchMaker], match_id: str):
        matchup = await interaction.client.database.get_match(match_id)

        if not matchup:
            return await interaction.followup.send(content="❌ **I couldn't find a match with that ID**")
        
        if not is_admin(interaction.user) and interaction.user.id in [matchup.team_one.player_one, matchup.team_one.player_two, matchup.team_two.player_one, matchup.team_two.player_two]:
            return await interaction.followup.send(content="❌ **You can't forcibly set the result of one of your own matches**")
        
        # TODO
        # use modal to input scores
        # log score
        
async def setup(bot: MatchMaker):
    cog = ForceResult(bot)
    
    for command in cog.walk_app_commands():
        if hasattr(command, "callback"):
            setattr(command.callback, "__name__", f"{cog.qualified_name.lower()}_{command.callback.__name__}")
            setattr(command, "guild_only", True)
    
    await bot.add_cog(cog)