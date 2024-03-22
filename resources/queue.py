import asyncio
import discord
import random
import time

from typing import Any, Union

from .objects import Object
from .database import Database
from .models import Match

class Queue:
    def __init__(self, database: Database):
        self.database  = database
        self.queue     = []
        self.increment = 1

    async def join_queue(self, team: Object[str, Any], loop: asyncio.AbstractEventLoop) -> Union[Object, Match]:
        if self.queue:
            for item in self.queue:
                if item.team.region != team.region:
                    continue

                if not item.team.vip_url and not team.vip_url:
                    continue

                # TODO:
                # match matching
                #   skill based
                
                # Example of simple skill based match making
                
                #if abs(item.team.trophies - team.trophies) > 100:
                #   continue

                match  = await self.database.create_match(self._create_id(), discord.utils.utcnow(), item.team.region, item.team, team)
                future = item.future.set_result(match)
                
                self.queue.remove(item)
                
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