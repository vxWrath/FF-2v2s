import datetime

from pydantic import BaseModel, Field, ConfigDict, field_serializer
from typing import Dict, Optional, Any, List
from enum import Enum
from enum import property as enum_property

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
    
class CheckFailureType:
    staff = 1
    admin = 1
    
class Model(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def model_dump(self, *args, **kwargs) -> Object:
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
    trophies: int = 0

    banned: bool = False
    banned_until: Optional[datetime.datetime] = None

    settings: Object = Field(default_factory=lambda: Object(
        region = 1, 
        party_requests = True, 
        party_request_whitelist = [],
        party_request_blacklist = [], 
    ))
    record: Object = Field(default_factory=lambda: Object(
        total_wins    = 0,
        total_losses  = 0,
        season_wins   = 0,
        season_losses = 0,
    ))
    
    @field_serializer("settings")
    def settings_to_dict(mapping: Any) -> dict:
        return mapping.convert()
    
    @field_serializer("record")
    def record_to_dict(mapping: Any) -> dict:
        return mapping.convert()
    
class Match(Model):
    id: int
    created_at: datetime.datetime
    region: int

    thread: Optional[int] = None
    score_message: Optional[int] = None

    team_one: Object
    team_two: Object
    
    scores: Object
    flags: Object = Field(default_factory=lambda: Object(
        pinged_players = False,
        pinged_staff = False,
        pinged_force = False,
    ))

    @field_serializer("team_one")
    def team_one_to_dict(mapping: Any) -> dict:
        return mapping.convert()
    
    @field_serializer("team_two")
    def team_two_to_dict(mapping: Any) -> dict:
        return mapping.convert()
    
    @field_serializer("scores")
    def scores_to_dict(mapping: Any) -> dict:
        return mapping.convert()
    
    @field_serializer("flags")
    def flags_to_dict(mapping: Any) -> dict:
        return mapping.convert()