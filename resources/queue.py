import asyncio
import discord

from typing import Any
from .objects import Object
from .database import Database

class Match:
    def __init__(self, team_one: Object[str, Any], team_two: Object[str, Any]):
        self.team_one = team_one
        self.team_two = team_two
        
    def __str__(self) -> str:
        return f"{self.team_one.name} vs {self.team_two.name}"
    
    def __repr__(self) -> str:
        return self.__str__()

class Queue:
    def __init__(self):#, database: Database):
        #self.database = database
        self.queue    = []

    async def join_queue(self, team: Object[str, Any], loop: asyncio.AbstractEventLoop):
        if self.queue:
            for item in self.queue:
                # TODO:
                # create match
                #   create ID
                #   store in database (in this func or /queue command)
                # match matching
                #   same region
                #   skill based
                
                # Example of simple skill based match making
                
                #if abs(item.team.trophies - team.trophies) > 100:
                #   continue
                
                match  = Match(item.team, team)
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