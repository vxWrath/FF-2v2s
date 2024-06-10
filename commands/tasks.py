import asyncio
import colorlog
import datetime
import discord

from discord.ext import commands, tasks
from resources import MatchMaker, Colors, Object, log_score, trophy_change, get_config

logger = colorlog.getLogger("bot")

class Tasks(commands.Cog):
    def __init__(self, bot: MatchMaker):
        self.bot = bot

    async def cog_load(self):
        self.bot.loop.create_task(self.start_tasks())

    async def start_tasks(self):
        await self.bot.wait_until_ready()

        functions = [getattr(self, func) for func in dir(self) if callable(getattr(self, func))]
        for func in functions:
            if isinstance(func, tasks.Loop):
                func.start()

    async def cog_unload(self):
        functions = [getattr(self, func) for func in dir(self) if callable(getattr(self, func))]
        for func in functions:
            if isinstance(func, tasks.Loop):
                func.cancel()

    @tasks.loop(minutes=15)
    async def auto_result(self):
        logger.debug("Running auto-result")

        config = get_config()
        now    = discord.utils.utcnow()
        guild  = self.bot.get_guild(config.MAIN_GUILD)

        for matchup in await self.bot.database.get_unfinished_matches():
            thread = guild.get_thread(matchup.thread) 

            if not thread:
                logger.info(f"Deleted Match ID {matchup.id}")
                return await self.bot.database.delete_match(matchup)

            if matchup.created_at + datetime.timedelta(hours=24) < now:
                max_voters  = max([len(voters) for voters in matchup.scores.values()] or [0])
                tied_scores = {score: voters for score, voters in matchup.scores.items() if len(voters) == max_voters}

                if not tied_scores or len(tied_scores.keys()) > 1:
                    embed = discord.Embed(
                        description = f"### It has been 24 hours since this game started, please force cancel or force the result of this match with `/force`",
                        color = Colors.blank
                    )

                    await thread.send(
                        content = f"<@&{config.STAFF_ROLE}>",
                        embed   = embed
                    )
                else:
                    await thread.send(
                        content = f"**Result automatically set. Deleting {discord.utils.format_dt(discord.utils.utcnow() + datetime.timedelta(seconds=10), "R")}**",
                    )

                    team_one_score, team_two_score = tuple(list(tied_scores.keys())[0].split('-'))

                    matchup.team_one.score = int(team_one_score)
                    matchup.team_two.score = int(team_two_score)
                    
                    self.bot.states.pop(matchup.team_one.player_one, None)
                    self.bot.states.pop(matchup.team_one.player_two, None)
                    self.bot.states.pop(matchup.team_two.player_one, None)
                    self.bot.states.pop(matchup.team_two.player_two, None)
                    
                    await asyncio.sleep(10)
                    await thread.delete()
                    
                    matchup.thread = None
                    matchup.score_message = None
                    matchup.scores = Object()

                    team_one_change = trophy_change(matchup.team_one, matchup.team_two)
                    team_two_change = trophy_change(matchup.team_two, matchup.team_one)

                    for player in [matchup.team_one.player_one, matchup.team_one.player_two]:
                        user = await self.bot.database.produce_user(player)
                        user.trophies = max(user.trophies + team_one_change, 0)

                        await self.bot.database.update_user(user)

                    for player in [matchup.team_two.player_one, matchup.team_two.player_two]:
                        user = await self.bot.database.produce_user(player)
                        user.trophies = max(user.trophies + team_two_change, 0)

                        await self.bot.database.update_user(user)
                    
                    await log_score(self.bot, matchup, list(tied_scores.values())[0], forced=True)

                matchup.flags.pinged_force = True
                await self.bot.database.update_match(matchup)
            elif not matchup.flags.pinged_staff and matchup.created_at + datetime.timedelta(hours=2) < now:
                embed = discord.Embed(
                    description = f"### The score of this matchup has still not been reported after 2 hours",
                    color = Colors.blank
                )

                await thread.send(
                    content = f"<@&{config.STAFF_ROLE}>",
                    embed   = embed
                )

                matchup.flags.pinged_staff = True
                await self.bot.database.update_match(matchup)
            elif not matchup.flags.pinged_players and matchup.created_at + datetime.timedelta(hours=1, minutes=30) < now:
                embed = discord.Embed(
                    description = f"### Please report the score of this matchup with `/result`",
                    color = Colors.blank
                )

                await thread.send(
                    content = f"<@{matchup.team_one.player_one}> <@{matchup.team_one.player_two}> <{matchup.team_two.player_one}> <{matchup.team_two.player_two}>", # ping players
                    embed   = embed
                )

                matchup.flags.pinged_players = True
                await self.bot.database.update_match(matchup)

        logger.debug("Finished auto-result")

    @auto_result.error
    async def error(self, error: Exception):
        self.auto_result.cancel()

        logger.error("Task failed to finish", exc_info=error)

async def setup(bot: MatchMaker):
    await bot.add_cog(Tasks(bot))