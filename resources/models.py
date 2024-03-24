from typing_extensions import Literal
from pydantic import BaseModel, Field, ConfigDict, field_serializer
from typing import Dict, Optional, Any, List, TypedDict
from enum import Enum
from enum import property as enum_property
import datetime

from .objects import Object

class Extras:
    def __init__(self, 
        defer: Optional[bool]=None, 
        defer_ephemerally: Optional[bool]=None,
        thinking: Optional[bool]=None,
        user_data: Optional[bool]=None,
        custom_id: Optional[Object] = None,
    ) -> None:
        self.defer = defer
        self.defer_ephemerally = defer_ephemerally
        self.thinking = thinking
        self.user_data = user_data
        self.custom_id = custom_id

class Region(Enum):
    US_East = 1
    US_West = 2
    Europe  = 3
    
    @enum_property
    def name(self):
        return self._name_.replace('_', ' ')
    
class Model(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def model_dump(self, *args, **kwargs) -> Dict[str, Any]:
        dump = super().model_dump(*args, **kwargs)
        return Object(dump)
    
    def dump_without_id(self) -> Object:
        item = self.model_dump()
        item.pop('id', None)
        item.pop('_id', None)
        
        return item

class User(Model):
    id: int
    roblox_id: Optional[int] = None
    blacklisted: Optional[bool] = False
    
    trophies: Optional[int] = 0
    wins: Optional[int] = 0
    losses: Optional[int] = 0
    
    inactive_for: Optional[int] = 0
    bonus: Optional[int] = 0

    settings: Optional[Object] = Field(default_factory=lambda: Object(
        region = 1, 
        queue_requests = True, 
        queue_request_whitelist = [],
        queue_request_blacklist = [], 
    ))
    
    season: Optional[Object] = Field(default_factory=lambda: Object({}))
    
    @field_serializer("settings")
    def settings_to_dict(mapping: Object):
        return mapping.convert()
    
    @field_serializer("season")
    def season_to_dict(mapping: Object):
        return mapping.convert()
    
class Match(Model):
    id: int
    created_at: datetime.datetime
    region: int

    thread_id: Optional[int] = None

    team_one: Object[str, Any] 
    team_two: Object[str, Any]

    @field_serializer("team_one")
    def team_one_to_dict(mapping: Object):
        return mapping.convert()
    
    @field_serializer("team_two")
    def team_two_to_dict(mapping: Object):
        return mapping.convert()