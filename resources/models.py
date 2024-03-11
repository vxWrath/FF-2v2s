from typing_extensions import Literal
from pydantic import BaseModel, Field, ConfigDict, field_serializer
from typing import Dict, Optional, Any, List
from enum import Enum

from .objects import Object

class Region(Enum):
    US_East = 1
    US_West = 2
    Europe  = 3
    
class Model(BaseModel):
    def model_dump(self, *args, **kwargs) -> Dict[str, Any]:
        dump = super().model_dump(*args, **kwargs)
        return Object(dump)
    
    def dump_without_id(self) -> Object:
        item = self.model_dump()
        item.pop('id', None)
        item.pop('_id', None)
        
        return item

class User(Model):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    id: int
    roblox_id: Optional[int] = None
    trophies: Optional[int] = 0
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