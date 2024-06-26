import asyncio
import datetime
import discord
import collections
import numpy

from discord import app_commands
from discord.ext import commands

from resources import MatchMaker, Extras, Colors, Object, log_score, trophy_change, send_thread_log, Config, Unverified, match_thread_only

class Result(commands.Cog):
    def __init__(self, bot: MatchMaker):
        self.bot: MatchMaker = bot

    @app_commands.command(
        name="result", 
        description="report the score & stats of a matchup",
        extras = Extras(defer=True, user_data=True)
    )
    @app_commands.describe(your_score="your team's score", opponents_score="your opponent's score")
    @app_commands.rename(your_score="your-score", opponents_score="opponents-score")
    @match_thread_only()
    async def result(self, interaction: discord.Interaction[MatchMaker], 
        your_score: app_commands.Range[int, 0, 100], 
        opponents_score: app_commands.Range[int, 0, 100]
    ):
        data = interaction.extras['users'][interaction.user.id]
        rblx = await self.bot.roblox_client.get_user(data.roblox_id)
        
        if not rblx:
            raise Unverified(interaction.user)
        
        matchup = await interaction.client.database.get_match_by_thread(interaction.channel.id)
        
        if not matchup:
            return await interaction.followup.send(content=f"❌ **I couldn't find the matchup within this thread**")
        
        if matchup.team_one.score is not None or matchup.team_two.score is not None:
            return await interaction.followup.send(content=f"❌ **The result of this matchup has already been set**")
        
        if not interaction.user.id in [
            matchup.team_one.player_one, 
            matchup.team_one.player_two, 
            matchup.team_two.player_one, 
            matchup.team_two.player_two,
        ]:
            return await interaction.followup.send(content=f"❌ **You do not have permission to set the result of this matchup**")
        
        yours    = matchup.team_one if interaction.user.id in [matchup.team_one.player_one, matchup.team_one.player_two] else matchup.team_two
        opponent = matchup.team_two if yours == matchup.team_one else matchup.team_one
        
        is_team_one = yours == matchup.team_one
        
        if matchup.score_message:
            message = interaction.channel.get_partial_message(matchup.score_message)
            
            try:
                await message.delete()
            except discord.HTTPException:
                pass
            
        score = f"{your_score}-{opponents_score}" if is_team_one else f"{opponents_score}-{your_score}"
        
        for temp_score, voters in matchup.scores.items():
            if interaction.user.id in voters:
                matchup.scores[temp_score].remove(interaction.user.id)
            
        if matchup.scores.get(score):
            matchup.scores[score].append(interaction.user.id)
            matchup.scores[score] = list(collections.OrderedDict.fromkeys(matchup.scores[score]))
        else:
            matchup.scores[score] = [interaction.user.id]
            
        matchup.scores = Object({x: y for x, y in matchup.scores.items() if y})
            
        embed = discord.Embed(
            description = f"## Matchup Scores\n",
            color = Colors.blank
        )
        embed.set_author(name="For a score to be confirmed, it must have 3/4 agreement")
        embed.set_footer(text=f"Type /result to vote - ID: {matchup.id}")
        
        for score, voters in dict(sorted(matchup.scores.items(), key=lambda x : len(x[1]), reverse=True)).items():
            team_one_score, team_two_score = tuple(score.split('-'))
            
            if len(voters) >= 2:
                matchup.log_message = await send_thread_log(matchup, interaction.channel)

                await interaction.followup.send(
                    content = f"**Result set. Deleting {discord.utils.format_dt(discord.utils.utcnow() + datetime.timedelta(seconds=10), "R")}**",
                )
            
                matchup.team_one.score = int(team_one_score)
                matchup.team_two.score = int(team_two_score)
                
                interaction.client.states.remove([
                    matchup.team_one.player_one, 
                    matchup.team_one.player_two, 
                    matchup.team_two.player_one,
                    matchup.team_two.player_two
                ])
                
                await asyncio.sleep(10)
                await interaction.channel.delete()
                
                matchup.thread = None
                matchup.score_message = None
                matchup.scores = Object()

                team_one_change = trophy_change(matchup.team_one, matchup.team_two)
                team_two_change = trophy_change(matchup.team_two, matchup.team_one)

                for player in [matchup.team_one.player_one, matchup.team_one.player_two]:
                    user = await interaction.client.database.produce_user(player)
                    user.trophies = max(user.trophies + team_one_change, 0)

                    if matchup.team_one.score > matchup.team_two.score:
                        user.record.total_wins += 1
                        user.record.season_wins += 1
                    else:
                        user.record.total_losses += 1
                        user.record.season_losses += 1

                    await interaction.client.database.update_user(user)

                for player in [matchup.team_two.player_one, matchup.team_two.player_two]:
                    user = await interaction.client.database.produce_user(player)
                    user.trophies = max(user.trophies + team_two_change, 0)

                    if matchup.team_one.score > matchup.team_two.score:
                        user.record.total_losses += 1
                        user.record.season_losses += 1
                    else:
                        user.record.total_wins += 1
                        user.record.season_wins += 1

                    await interaction.client.database.update_user(user)
                
                await interaction.client.database.update_match(matchup)
                return await log_score(interaction.client, matchup, voters, forced=False)
            
            embed.description += f"`{team_one_score:>2}` **- <@{matchup.team_one.player_one}> & <@{matchup.team_one.player_two}>**\n"
            embed.description += f"`{team_two_score:>2}` **- <@{matchup.team_two.player_one}> & <@{matchup.team_two.player_two}>**\n"
            
            embed.description += f"*- Voters (`{(len(voters) / 3) * 100:.0f}%`): " + ", ".join([f"<@{x}>" for x in voters]) + "*\n\n"
        
        message = await interaction.followup.send(embed=embed)
        
        matchup.score_message = message.id
        await interaction.client.database.update_match(matchup)
        
async def setup(bot: MatchMaker):
    cog = Result(bot)
    
    for command in cog.walk_app_commands():
        if hasattr(command, "callback"):
            setattr(command.callback, "__name__", f"{cog.qualified_name.lower()}_{command.callback.__name__}")
            setattr(command, "guild_only", True)
    
    await bot.add_cog(cog)