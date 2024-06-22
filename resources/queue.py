from __future__ import annotations

import asyncio
import discord
import random
import time

from typing import Any, Union, TYPE_CHECKING

from .config import Config
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
        
    async def join_queue(self, team: Object) -> Union[Object, Match]:
        future = self.bot.loop.create_future()
        item   = Object(team=team, future=future, trophy_search_range=INITIAL_SEARCH_RANGE)

        self.queue.append(item)
        self.bot.loop.create_task(self.increment_loop(item))

        try:
            await future
            return future.result()
        except Exception as e:
            raise e
        
    async def find_matchup(self, item: Object) -> bool:
        for queue_item in self.queue:
            if (
                item == queue_item or 
                item.team.region != queue_item.team.region or 
                not item.team.private_server and not queue_item.team.private_server
            ):
                continue

            average_search_range = (item.trophy_search_range + queue_item.trophy_search_range) / 2
            if abs(queue_item.team.trophies - item.team.trophies) > average_search_range:
                continue
            
            if self.bot.production:
                player_one_opps = await self.database.get_user_recent_opponents(item.team.player_one)
                player_two_opps = await self.database.get_user_recent_opponents(item.team.player_one)

                if queue_item.team.player_one in player_one_opps + player_two_opps or queue_item.team.player_two in player_one_opps + player_two_opps:
                    continue

            self.queue.remove(item)
            self.queue.remove(queue_item)

            config  = Config.get()
            channel = self.bot.get_channel(config.THREAD_CHANNEL)

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
                    f"### Team One (🏆 {queue_item.team.trophies})\n"
                    f"<@{queue_item.team.player_one}> (`{queue_item.team.player_one}`)\n"
                    f"<@{queue_item.team.player_two}> (`{queue_item.team.player_two}`)\n"
                    f"### Team Two (🏆 {item.team.trophies})\n"
                    f"<@{item.team.player_one}> (`{item.team.player_one}`)\n"
                    f"<@{item.team.player_two}> (`{item.team.player_two}`)\n"
                ),
                color = Colors.blank,
                timestamp = discord.utils.utcnow(),
            )
            
            message = await thread.send(
                content=f"<@{queue_item.team.player_one}> <@{queue_item.team.player_two}> <@{item.team.player_one}> <@{item.team.player_two}>",
                embed=embed,
            )
            
            await asyncio.sleep(1)

            if item.team.private_server and item.team.private_server:
                await message.reply(content=(
                    f"`Team One's Private Server:` **{queue_item.team.private_server}**\n"
                    f"`Team Two's Private Server:` **{item.team.private_server}**"
                ), suppress_embeds=True)
            elif item.team.private_server:
                await message.reply(content=(
                    f"`Team Two's Private Server:` **{item.team.private_server}**"
                ), suppress_embeds=True)
            elif queue_item.team.private_server:
                await message.reply(content=(
                    f"`Team One's Private Server:` **{queue_item.team.private_server}**\n"
                ), suppress_embeds=True)
                
            await message.reply(content=f":bangbang: `Match ID:` **{match_id}**")

            match  = await self.database.create_match(match_id, discord.utils.utcnow(), item.team.region, thread.id, queue_item.team, item.team)
            
            item.future.set_result(match)
            queue_item.future.set_result(match)
            
            return True

    async def increment_loop(self, item: Object):
        while True:
            found_match = await self.find_matchup(item)

            if found_match:
                return

            increment_task = self.bot.loop.create_task(asyncio.sleep(INCREMENT_INTERVAL))

            done, _ = await asyncio.wait([increment_task, item.future], timeout=600, return_when=asyncio.FIRST_COMPLETED)

            if not done:
                return self.queue.remove(item)
            
            first_completed = done.pop()

            if first_completed == increment_task:
                if item.trophy_search_range >= MAX_SEARCH_RANGE:
                    continue
                item.trophy_search_range += INCREMENT_RANGE
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