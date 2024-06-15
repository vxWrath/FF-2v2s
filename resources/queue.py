from __future__ import annotations

import asyncio
import discord
import random
import time

from typing import Any, Union, TYPE_CHECKING

from .objects import Object
from .database import Database
from .models import Match
from .utils import Colors

if TYPE_CHECKING:
    from .matchmaker import MatchMaker

INITIAL_SEARCH_RANGE = 100
INCREMENT_RANGE      = 50
INCREMENT_INTERVAL   = 15 # every 15 seconds, search range increases by 50
MAX_SEARCH_RANGE     = 1000

class Queue:
    def __init__(self, bot: MatchMaker):
        self.bot       = bot
        self.database  = bot.database
        self.queue     = []
        self.increment = 1

    async def join_queue(self, team: Object, channel: discord.TextChannel) -> Union[Object, Match]:
        if self.queue:
            for item in self.queue:
                if item.team.region != team.region:
                    continue

                if not item.team.private_server and not team.private_server:
                    continue
                
                average_search_range = (INITIAL_SEARCH_RANGE + item.trophy_search_range) / 2
                if abs(item.team.trophies - team.trophies) > average_search_range:
                    continue
                
                if self.bot.production:
                    player_one_opps = await self.database.get_user_recent_opponents(team.player_one)
                    player_two_opps = await self.database.get_user_recent_opponents(team.player_one)

                    if item.team.player_one in player_one_opps + player_two_opps or item.team.player_two in player_one_opps + player_two_opps:
                        continue

                self.queue.remove(item)
                
                match_id = self._create_id()
                thread   = await channel.create_thread(
                    name = f"2v2: {match_id}", 
                    message = None,
                    type = discord.ChannelType.private_thread,
                    invitable = False,
                    auto_archive_duration = 1440
                )
                
                embed = discord.Embed(
                    description = (
                        f"# 2v2 Matchup\n"
                        f":bangbang: `Match ID:` **{match_id}**\n"
                        f"### Team One (🏆 {item.team.trophies})\n"
                        f"<@{item.team.player_one}> (`{item.team.player_one}`)\n"
                        f"<@{item.team.player_two}> (`{item.team.player_two}`)\n"
                        f"### Team Two (🏆 {team.trophies})\n"
                        f"<@{team.player_one}> (`{team.player_one}`)\n"
                        f"<@{team.player_two}> (`{team.player_two}`)\n"
                    ),
                    color = Colors.blank,
                    timestamp = discord.utils.utcnow(),
                )
                
                message = await thread.send(
                    content=f"<@{item.team.player_one}> <@{item.team.player_two}> <@{team.player_one}> <@{team.player_two}>",
                    embed=embed,
                )
                
                await asyncio.sleep(1)
                
                if team.private_server and item.team.private_server:
                    await message.reply(content=(
                        f"`Team One's Private Server:` **{item.team.private_server}**\n"
                        f"`Team Two's Private Server:` **{team.private_server}**"
                    ), suppress_embeds=True)
                elif team.private_server:
                    await message.reply(content=(
                        f"`Team Two's Private Server:` **{team.private_server}**"
                    ), suppress_embeds=True)
                elif item.team.private_server:
                    await message.reply(content=(
                        f"`Team One's Private Server:` **{item.team.private_server}**\n"
                    ), suppress_embeds=True)
                    
                await message.reply(content=f":bangbang: `Match ID:` **{match_id}**")
                    
                match  = await self.database.create_match(match_id, discord.utils.utcnow(), item.team.region, thread.id, item.team, team, Object({}), None)
                future = item.future.set_result(match)
                
                return match
        
        future = self.bot.loop.create_future()
        item   = Object(team=team, future=future, queued_since=discord.utils.utcnow(), trophy_search_range=INITIAL_SEARCH_RANGE)

        self.queue.append(item)
        self.bot.loop.create_task(self.increment(item))

        try:
            await future
            return future.result()
        except Exception as e:
            raise e
        
    async def increment(self, item: Object):
        while True:
            increment_task = self.bot.loop.create_task(asyncio.sleep(INCREMENT_INTERVAL))

            done, _ = await asyncio.wait([increment_task, item.future], timeout=600, return_when=asyncio.FIRST_COMPLETED)

            if not done:
                return self.queue.remove(item)
            
            first_completed = done.pop()

            if first_completed == increment_task:
                item.trophy_search_range += INCREMENT_RANGE

                if item.trophy_search_range >= MAX_SEARCH_RANGE:
                    return
            else:
                return increment_task.cancel()

    def _create_id(self) -> int:
        base    = str(discord.utils.DISCORD_EPOCH - int(time.time()))
        special = [str(self.increment)] + [str(random.randint(0, 9)) for _ in range(5 - len(str(self.increment)))]

        if self.increment == 999:
            self.increment = 1
        else:
            self.increment += 1

        random.shuffle(special)
        return int(base + ''.join(special))
    
async def setup(_):
    pass