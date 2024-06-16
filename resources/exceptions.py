import discord
from typing import Union

from .models import User, CheckFailureType

class MatchMakerException(Exception):
    pass

class Unverified(MatchMakerException):
    def __init__(self, member: discord.Member):
        self.member = member

class CheckFailure(discord.app_commands.CheckFailure):
    def __init__(self, type: CheckFailureType):
        self.type = type

class MemberBanned(MatchMakerException):
    def __init__(self, member: discord.Member, data: User):
        self.member = member
        self.data   = data