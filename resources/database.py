from os import environ as env
from typing import Optional, List, Type

import asyncio
import json
import datetime
import subprocess
import sys

from redis.asyncio import Redis
from redis import ConnectionError as RedisConnectionError
from redis import AuthenticationError as RedisAuthenticationError
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import DuplicateKeyError

from .objects import BaseObject, Object, ObjectArray
from .models import User

MONGO_URL = env['MONGO_URL']
REDIS_PASSWORD = env['REDIS_PASSWORD']
        
class Database:
    def __init__(self):
        self.mongo = AsyncIOMotorClient(MONGO_URL, tz_aware=True)
        self.mongo.get_io_loop = asyncio.get_running_loop
        
        self.redis = Redis(
            password = REDIS_PASSWORD,
            decode_responses = True,
            retry_on_timeout = True,
            health_check_interval = 30,
        )
        
    async def ping_loop(self):
        errors = 0
        while True:
            try:
                await asyncio.wait_for(self.redis.ping(), timeout=10)
            except RedisAuthenticationError as e:
                self.redis = Redis(
                    decode_responses = True,
                    retry_on_timeout = True,
                    health_check_interval = 30,
                )
            except RedisConnectionError as e:
                if errors > 0 or sys.platform != 'win32':
                    raise SystemError("Failed to connect to Redis.") from e
                else:
                    errors += 1
                    subprocess.run("wsl sudo -S sudo service redis-server start", input=f"{REDIS_PASSWORD}\n\n".encode(), shell=True)

            await asyncio.sleep(10)
           
    async def create[T](self, domain: str, item_id: str, cls: Type[T]) -> T:
        item = cls(**{"id": int(item_id)})
        
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
    
    async def update_user(self, user: User, update_keys: Optional[List[str]]=None) -> None:
        items = user.dump_without_id()
        
        if update_keys:
            return await self.update(
                "users",
                str(user.id),
                True,
                **{k: v for k, v in items.items() if k in update_keys}
            )
            
        return await self.update(
            "users",
            str(user.id),
            True
            **items
        )
        
    async def produce_user(self, user_id: int) -> User:
        user = await self.get_user(user_id)
        
        if user is None:
            user = await self.create_user(user_id)
            
        return user