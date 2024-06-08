import discord
from typing import Union

class MatchMakerException(Exception):
    pass

class NoRobloxUser(MatchMakerException):
    def __init__(self, member: Union[discord.User, discord.Member]):
        self.member = member