from os import environ as env
from typing import Optional, List, Type, Any

import asyncio
import datetime

from redis.asyncio import Redis
from redis import ConnectionError as RedisConnectionError
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import DuplicateKeyError

from .objects import Object
from .models import User, Match

MONGO_URL = env['MONGO_URL']
        
class Database:
    def __init__(self):
        self.mongo = AsyncIOMotorClient(MONGO_URL, tz_aware=True)
        self.mongo.get_io_loop = asyncio.get_running_loop
        
        self.redis = Redis(
            decode_responses = True,
            retry_on_timeout = True,
            health_check_interval = 30,
        )
        
    async def ping_loop(self):
        while True:
            try:
                await asyncio.wait_for(self.redis.ping(), timeout=10)
            except RedisConnectionError as e:
                raise e

            await asyncio.sleep(30)
           
    async def create[T](self, domain: str, item_id: str, cls: Type[T], **aspects) -> T:
        item = cls(**{"id": int(item_id)} | aspects)
        
        try:
            await self.mongo.matchmaker[domain].insert_one({"_id": str(item_id)} | item.dump_without_id().to_mongo())
        except DuplicateKeyError:
            pass
            
        return item
        
    async def get[T](self, domain: str, item_id: str, cls: Type[T], mongo: bool) -> Optional[T]:
        item = Object.from_redis((await self.redis.hgetall(f"{domain}:{item_id}")) or {})

        if mongo and not item:
            item = Object.from_mongo((await self.mongo.matchmaker[domain].find_one({"_id": str(item_id)}) or {}))
            
            if item:
                item.pop("_id")
                
                async with self.redis.pipeline() as pipe:
                    await pipe.hset(f"{domain}:{item_id}", mapping=item.to_redis())
                    await pipe.expire(f"{domain}:{item_id}", int(datetime.timedelta(hours=1).total_seconds()))
                    await pipe.execute()
            
        if not item:
            return
        
        if item.get("_id"):
            item.pop("_id")
            
        item["id"] = int(item_id) if item_id.isdigit() else item_id
        return cls(**item)
    
    async def update(self, domain: str, item_id: str, mongo: bool, **aspects) -> None:
        setting   = Object({x: y for x, y in aspects.items() if y != None})
        unsetting = Object({x: y for x, y in aspects.items() if y == None})
        
        if setting:
            setting.pop('id', None)
            setting.pop('_id', None)
            
            async with self.redis.pipeline() as pipe:
                await pipe.hset(f"{domain}:{item_id}", mapping=setting.to_redis())
                await pipe.expire(f"{domain}:{item_id}", int(datetime.timedelta(hours=1).total_seconds()))
                await pipe.execute()
                
        if unsetting:
            await self.redis.hdel(f"{domain}:{item_id}", *unsetting.keys())
        
        if mongo:
            await self.mongo.matchmaker[domain].update_one({"_id": str(item_id)}, {"$set": setting.to_mongo(), "$unset": unsetting.to_mongo()})
        
    async def create_user(self, user_id: int) -> User:
        return await self.create("users", str(user_id), User)
    
    async def get_user(self, user_id: int) -> Optional[User]:
        return await self.get("users", str(user_id), User, True)
    
    async def update_user(self, user: User) -> None:
        items = user.dump_without_id()
            
        return await self.update(
            "users",
            str(user.id),
            True,
            **items
        )
        
    async def produce_user(self, user_id: int) -> User:
        user = await self.get_user(user_id)
        
        if user is None:
            user = await self.create_user(user_id)
            
        return user
    
    async def create_match(self, match_id: int, created_at: datetime.datetime, region: int, thread: int, team_one: Object[str, Any], team_two: Object[str, Any], scores: Object[str, List[int]], score_message: Optional[int]):
        return await self.create("matches", str(match_id), Match, **{
            "region": region, 
            "created_at": created_at,
            "thread": thread,
            "team_one": team_one,
            "team_two": team_two,
            "scores": scores,
            "score_message": score_message,
        })
        
    async def update_match(self, match: Match) -> None:
        items = match.dump_without_id()
        
        return await self.update(
            "matches",
            str(match.id),
            True,
            **items
        )
        
    async def delete_match(self, match: Match) -> None:
        await self.mongo.matchmaker["matches"].delete_one({"_id": str(match.id)})
        await self.redis.delete(f"matches:{match.id}")

    async def get_unfinished_matches(self) -> List[Match]:
        query = {
            "$and": [
                {"team_one.score": None},
                {"team_two.score": None},
            ],
        }
        
        return [Match(**_change_id(Object.from_mongo(x))) async for x in self.mongo.matchmaker["matches"].find(query)]
        
    async def get_match_by_thread(self, thread_id: int) -> Optional[Match]:
        item = Object.from_mongo((await self.mongo.matchmaker["matches"].find_one({"thread": str(thread_id)}) or {}))
        
        if not item:
            return
        
        item["id"] = item.pop("_id")
        return Match(**item)
    
    async def get_user_matches(self, user_id: int) -> Optional[List[Match]]:
        query = {
            "$or": [
                {"team_one.player_one": str(user_id)},
                {"team_one.player_two": str(user_id)},
                {"team_two.player_one": str(user_id)},
                {"team_two.player_two": str(user_id)}
            ]
        }
        
        return [Match(**_change_id(Object.from_mongo(x))) async for x in self.mongo.matchmaker["matches"].find(query)]
    
    async def get_user_recent_opponents(self, user_id: int) -> List[int]:
        query = {
            "$or": [
                {"team_one.player_one": str(user_id)},
                {"team_one.player_two": str(user_id)},
                {"team_two.player_one": str(user_id)},
                {"team_two.player_two": str(user_id)}
            ],
            "created_at": {"$gte": datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(hours=36)}
        }

        all_opponents = [
            [x["team_one"]["player_one"], x["team_one"]["player_two"], x["team_two"]["player_one"], x["team_two"]["player_two"]] 
            async for x in self.mongo.matchmaker["matches"].find(query)
        ]

        if not all_opponents:
            return []

        recent_opps = {int(opp) for matchup in all_opponents for opp in matchup}
        recent_opps.remove(user_id)

        return list(recent_opps)
    
def _change_id(item: Object) -> Object:
    item["id"] = item.pop("_id")
    return item