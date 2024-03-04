from os import environ as env
from typing import Optional, List, Type

import asyncio
import json
import datetime

from redis.asyncio import Redis
from redis import ConnectionError as RedisConnectionError
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import DuplicateKeyError

from .objects import BaseObject, Object, ObjectArray
from .models import User

MONGO_URL = env['MONGO_URL']
REDIS_PASSWORD = env['REDIS_PASSWORD']

async def ping_loop(redis: Redis):
    while True:
        try:
            await asyncio.wait_for(redis.ping(), timeout=10)
        except RedisConnectionError as e:
            raise SystemError("Failed to connect to Redis.") from e

        await asyncio.sleep(10)
        
def to_redis(obj):
    return {
        k: json.dumps(v.regular(to_redis=True)) if isinstance(v, BaseObject) else v 
        for k, v in Object(obj).items()
        if v != None
    }
    
def from_redis(obj):
    if obj:
        for key, val in obj.items():
            try:
                obj[key] = json.loads(val)
            except json.JSONDecodeError:
                obj[key] = val
        
    return obj

class Database:
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.mongo = AsyncIOMotorClient(MONGO_URL, tz_aware=True)
        self.mongo.get_io_loop = asyncio.get_running_loop
        
        self.redis = Redis(
            password = REDIS_PASSWORD,
            decode_responses = True,
            retry_on_timeout = True,
            health_check_interval = 30,
        )
        
        loop.create_task(ping_loop(self.redis))
           
    async def create[T](self, domain: str, item_id: str, cls: Type[T]) -> T:
        item = cls(**{"id": int(item_id)})
        
        try:
            await self.mongo.matchmaker[domain].insert_one({"_id": str(item_id)} | item.dump())
        except DuplicateKeyError:
            pass
            
        return item
        
    async def get[T](self, domain: str, item_id: str, cls: Type[T]) -> Optional[T]:
        item = from_redis(await self.redis.hgetall(f"{domain}:{item_id}"))
            
        if not item:
            print('mongo')
            item = await self.mongo.matchmaker[domain].find_one({"_id": str(item_id)})
            
            if item:
                item.pop("_id")
                
                async with self.redis.pipeline() as pipe:
                    await pipe.hset(f"{domain}:{item_id}", mapping=to_redis(item))
                    await pipe.expire(f"{domain}:{item_id}", int(datetime.timedelta(hours=1).total_seconds()))
                    await pipe.execute()
            
        if not item:
            return
        
        if item.get("_id"):
            item.pop("_id")
            
        item["id"] = int(item_id)
        return cls(**item)
    
    async def update(self, domain: str, item_id: str, **aspects) -> None:
        setting   = {x: y for x, y in aspects.items() if y != None}
        unsetting = {x: y for x, y in aspects.items() if y == None}
        
        if setting:
            setting.pop('id', None)
            setting.pop('_id', None)
            
            async with self.redis.pipeline() as pipe:
                await pipe.hset(f"{domain}:{item_id}", mapping=to_redis(setting))
                await pipe.expire(f"{domain}:{item_id}", int(datetime.timedelta(hours=1).total_seconds()))
                await pipe.execute()
                
        if unsetting:
            await self.redis.hdel(f"{domain}:{item_id}", *unsetting.keys())
            
        await self.mongo.matchmaker[domain].update_one({"_id": str(item_id)}, {"$set": setting, "$unset": unsetting})
        
    async def create_user(self, user_id: int) -> User:
        return await self.create("users", str(user_id), User)
    
    async def get_user(self, user_id: int) -> Optional[User]:
        return await self.get("users", str(user_id), User)
    
    async def update_user(self, user: User, update_keys: List[str]) -> None:
        items = user.dump()
        
        return await self.update(
            "users",
            str(user.id),
            **{k: v for k, v in items.items() if k in update_keys}
        )