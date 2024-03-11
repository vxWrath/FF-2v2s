import datetime
import json

from typing import Dict, Any, Self, Optional

class BaseObject:
    @classmethod
    def from_mongo(cls: Self) -> Self:
        raise NotImplementedError()
        
    @classmethod
    def from_redis(cls: Self) -> Self:
        raise NotImplementedError()
    
    def to_mongo(self):
        raise NotImplementedError()
    
    def to_redis(self):
        raise NotImplementedError()
        
    def convert(self):
        raise NotImplementedError()
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.convert()})"
    
    __str__ = __repr__
    
class Object(BaseObject, dict):
    def __init__(self, mapping: Optional[dict]=None, **kwargs):
        mapping = mapping or {}
        mapping.update(kwargs)
        
        for key, val in mapping.items():
            if isinstance(val, dict):
                mapping[key] = Object(val)
            elif isinstance(val, list):
                mapping[key] = ObjectArray(val)
        
        super().__init__(mapping)
    
    def __getattr__(self, __key: Any) -> Any:
        return self.get(__key, None)
    
    def __setattr__(self, __name: str, __value: Any) -> None:
        self[__name] = __value
        
    def __delattr__(self, __name: str) -> None:
        del self[__name]
       
    def __getitem__(self, key: Any, splitter: Optional[str]=".") -> Any:
        try:
            if isinstance(key, str):
                keys = key.split(splitter)
            elif isinstance(key, tuple):
                keys = key
            else:
                keys = [key]
                
            val = self
            
            for key in keys:
                try:
                    val = dict.__getitem__(val, key)
                except TypeError:
                    val = getattr(val, str(key))
                
            return val
        except (KeyError, AttributeError):
            return
        
    def __setitem__(self, key: Any, value: Any, splitter: Optional[str]=".") -> None:
        if isinstance(key, str):
            keys = key.split(splitter)
        elif isinstance(key, tuple):
            keys = key
        else:
            keys = [key]

        val = self

        for k in range(len(keys)):
            current_key = keys[k]
            
            if k + 1 == len(keys):
                try:
                    return dict.__setitem__(val, current_key, value)
                except TypeError:
                    return setattr(val, str(current_key), value)
            
            try:
                val = val[current_key]
            except KeyError:
                val = getattr(val, str(current_key))
            except TypeError:
                raise TypeError(f"{'.'.join(keys[:k+1])} - '{val.__class__.__name__}' object is not subscriptable")
        
    def copy(self) -> Self:
        return Object(super().copy())
        
    def has(self, __key: Any) -> bool:
        return __key in self.keys()
        
    @classmethod
    def from_mongo(cls: Self, mapping: dict) -> Self:
        for key, val in mapping.items():
            if isinstance(val, dict):
                mapping[key] = cls.from_mongo(val)
            elif isinstance(val, str):
                if val.isdigit():
                    mapping[key] = int(val)
                elif val.replace('.', '').isdigit():
                    mapping[key] = float(val)
                else:
                    try:
                        mapping[key] = datetime.datetime.fromisoformat(val)
                    except ValueError:
                        pass
                    
        return cls(mapping)
                    
    @classmethod
    def from_redis(cls: Self, mapping: dict) -> Self:
        for key, val in mapping.items():
            if isinstance(val, str):
                try:
                    mapping[key] = datetime.datetime.fromisoformat(val)
                except ValueError:
                    pass
                
                try:
                    mapping[key] = json.loads(val)
                except json.JSONDecodeError:
                    mapping[key] = val
                        
        return cls(mapping)
        
    def to_mongo(self) -> dict:
        mapping = {}
        for key, val in self.items():
            if not isinstance(val, bool) and isinstance(val, (int, float)):
                mapping[key] = str(val)
            elif isinstance(val, datetime.datetime):
                mapping[key] = val.isoformat()
            elif isinstance(val, BaseObject):
                mapping[key] = val.to_mongo()
            else:
                mapping[key] = val
                
        return mapping
        
    def to_redis(self) -> dict:
        mapping = {}
        for key, val in self.items():
            if val == None:
                continue
            
            if isinstance(val, datetime.datetime):
                mapping[key] = val.isoformat()
            elif isinstance(key, BaseObject):
                mapping[key] = json.dumps(val.to_redis())
            else:
                mapping[key] = json.dumps(val)
                
        return mapping
        
    def convert(self) -> dict:
        return {
            key: val.convert() if isinstance(val, BaseObject) else val
            for key, val in self.items()
        }
        
class ObjectArray(BaseObject, list):
    def __init__(self, array: Optional[list]=None, *args):
        array = array or []
        array.extend(list(args))
        
        for i in range(len(array)):
            if isinstance(array[i], dict):
                array[i] = Object(array[i])
            elif isinstance(array[i], list):
                array[i] = ObjectArray(array[i])

        super().__init__(array)
        
    @classmethod
    def from_mongo(cls: Self, array: list) -> Self:
        for i in range(len(array)):
            if isinstance(array[i], str):
                if array[i].isdigit():
                    array[i] = int(array[i])
                elif array[i].replace('.', '').isdigit():
                    array[i] = float(array[i])
                else:
                    try:
                        array[i] = datetime.datetime.fromisoformat(array[i])
                    except ValueError:
                        pass
                    
        return cls(array)
        
    @classmethod
    def from_redis(cls: Self, array: list) -> Self:
        for i in range(len(array)):
            if isinstance(array[i], str):
                try:
                    array[i] = datetime.datetime.fromisoformat(i)
                except ValueError:
                    pass
                
                try:
                    array[i] = json.loads(i)
                except json.JSONDecodeError:
                    pass
                        
        return cls(array)
    
    def to_mongo(self) -> list:
        array = []
        for i in range(len(self)):
            if isinstance(self[i], (int, float)):
                array[i] = str(self[i])
            elif isinstance(self[i], datetime.datetime):
                array[i] = self[i].isoformat()
            elif isinstance(self[i], BaseObject):
                array[i] = self[i].to_mongo()
            else:
                array[i] = self[i]
                
        return array
    
    def to_redis(self) -> list:
        array = []
        for i in range(len(self)):
            if self[i] == None:
                continue
            
            if isinstance(self[i], datetime.datetime):
                array[i] = self[i].isoformat()
            elif isinstance(self[i], BaseObject):
                array[i] = json.dumps(self[i].to_redis())
            else:
                array[i] = json.dumps(self[i])
        
    def convert(self) -> list: 
        return [
            x.convert() if isinstance(x, BaseObject) else x
            for x in self
        ]