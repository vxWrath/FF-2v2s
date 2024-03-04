from pydantic import BaseModel, Field
from typing import Dict, Optional
from enum import Enum

from .objects import Object

class Region(Enum):
    US_East = 1
    US_West = 2
    Europe  = 3
    
class Model(BaseModel):
    def dump(self):
        item = self.model_dump()
        item.pop('id', None)
        
        for key, val in item.items():
            if isinstance(val, int):
                item[key] = str(val)
        
        return item

class User(Model):
    id: int
    robloxID: Optional[str] = None
    region: Optional[int] = Region(1).value
    
    trophies: Optional[int] = 500
    inactive_for: Optional[int] = 0
    bonus: Optional[int] = 0
    season: Optional[Dict[str, int]] = Field(default_factory=lambda: Object({}))