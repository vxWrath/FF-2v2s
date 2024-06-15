import json
from .objects import Object

class Config:
    retreived: bool = False
    config: Object = Object({})

    def __str__(self):
        return f"Config(retreived={self.retreived})"
    
    @staticmethod
    def to_str():
        attrs = [
            f"{key}={value}" for key, value in Config.__dict__.items() 
            if not key.startswith('__') and not callable(value)
        ]

        return f"{Config.__name__}({', '.join(attrs)})"
    
    @staticmethod
    def get() -> Object:
        if not Config.retreived:
            with open('config.json', 'r') as f:
                return Object(json.load(f))
        return Config.config
    
    @staticmethod
    def update() -> None:
        with open('config.json', 'w') as f:
            json.dump(Config.config, f, indent=4)