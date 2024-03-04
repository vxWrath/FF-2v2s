import datetime
from typing import Dict, Any, Self, Optional

class BaseObject:
    def regular(self, to_redis: Optional[bool]=False):
        raise NotImplementedError()
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.regular()})"
    
    __str__ = __repr__
    
class Object(BaseObject, dict):
    def __init__(self, dictionary: Optional[dict]=None, convert_dt: Optional[bool]=True, **kwargs):
        dictionary = dictionary or {}  
        dictionary.update(kwargs)
        
        for key, val in dictionary.items():
            if isinstance(val, dict):
                dictionary[key] = Object(val, convert_dt=convert_dt)
            elif isinstance(val, list):
                dictionary[key] = ObjectArray(val, convert_dt=convert_dt)
            elif convert_dt and isinstance(val, str) and not val.isdigit():
                try:
                    print(convert_dt, val)
                    dictionary[key] = datetime.datetime.fromisoformat(val)
                except ValueError:
                    pass
        
        super().__init__(dictionary)
        
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
        
    def regular(self, to_redis: Optional[bool]=False):
        if to_redis:
            return {
                key: val.regular(to_redis=to_redis) if isinstance(val, (Object, ObjectArray))
                else val.isoformat() if isinstance(val, datetime.datetime)
                else val for key, val in self.items()
            }
        
        return {
            key: val.regular() if isinstance(val, (Object, ObjectArray))
            else val for key, val in self.items()
        }
        
class ObjectArray(BaseObject, list):
    def __init__(self, array: Dict[Any, Any], convert_dt: Optional[bool]=True):
        for i in range(len(array)):
            if isinstance(array[i], dict):
                array[i] = Object(array[i], convert_dt=convert_dt)
            elif isinstance(array[i], list):
                array[i] = ObjectArray(array[i], convert_dt=convert_dt)
            elif convert_dt and isinstance(array[i], str) and not array[i].isdigit():
                try:
                    array[i] = datetime.datetime.fromisoformat(array[i])
                except ValueError:
                    pass

        super().__init__(array)
        
    def regular(self, to_redis: Optional[bool]=False):
        if to_redis:
            return [
                x.regular(to_redis=to_redis) if isinstance(x, (Object, ObjectArray)) 
                else x.isoformat() if isinstance(x, datetime.datetime)
                else x for x in self
            ]
            
        return [
            x.regular() if isinstance(x, (Object, ObjectArray)) 
            else x for x in self
        ]

