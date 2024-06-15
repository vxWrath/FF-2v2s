import discord
from typing import Union

from .models import CheckFailureType

class MatchMakerException(Exception):
    pass

class NoRobloxUser(MatchMakerException):
    def __init__(self, member: Union[discord.User, discord.Member]):
        self.member = member

class CheckFailure(discord.app_commands.CheckFailure):
    def __init__(self, check: CheckFailureType):
        self.check = check