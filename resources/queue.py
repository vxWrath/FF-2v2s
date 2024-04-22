import asyncio
import discord
import random
import time

from typing import Any, Union

from .objects import Object
from .database import Database
from .models import Match
from .utils import Colors

class Queue:
    def __init__(self, database: Database):
        self.database  = database
        self.queue     = []
        self.increment = 1

    async def join_queue(self, team: Object[str, Any], loop: asyncio.AbstractEventLoop, channel: discord.TextChannel) -> Union[Object, Match]:
        if self.queue:
            for item in self.queue:
                if item.team.region != team.region:
                    continue

                #if not item.team.private_server and not team.private_server:
                #    continue

                # TODO:
                # match matching
                #   skill based
                #   progressive (trophy/match search widens every nth second)
                #   prohibit recent matches
                #       recent dates (maybe within 12-24 hours, possibly longer) and recent opponents
                
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
                    
                await message.reply(content=(
                    f":bangbang: `Match ID:` **{match_id}**"
                ), suppress_embeds=True)
                    
                match  = await self.database.create_match(match_id, discord.utils.utcnow(), item.team.region, thread.id, item.team, team, Object({}), None)
                future = item.future.set_result(match)
                
                return match
        
        future = loop.create_future()
        self.queue.append(Object(future=future, date=discord.utils.utcnow(), team=team))
        
        try:
            await future
            return future.result()
        except Exception as e:
            raise e
        
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