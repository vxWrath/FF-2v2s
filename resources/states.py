from __future__ import annotations

from typing import Literal, Optional, List, Dict, Iterator
from discord.ext.commands import Bot as MatchMaker
from discord.utils import utcnow

class States:
    def __init__(self, bot: MatchMaker):
        self.bot = bot
        self.states: Dict[int, PlayerState] = {}

    def __repr__(self) -> str:
        return (
            "<States "
            f"queueing={len([x for x in self.states.values() if x.action == "queueing"])} "
            f"playing={len([x for x in self.states.values() if x.action == "playing"])}"
        )
    
    def __iter__(self) -> Iterator[int]:
        return iter(self.states.keys())
    
    def keys(self) -> List[int]:
        return list(self.__iter__())
    
    def values(self) -> List[PlayerState]:
        return list(self.states.values())
    
    def items(self):
        return self.states.items()

    def __getitem__(self, player_id: int) -> Optional[PlayerState]:
        return self.states.get(player_id)

    def update(self, player_ids: List[int], new_action: Literal['playing', 'queueing']):
        for player_id in player_ids:
            if not self[player_id]:
                self.states[player_id] = PlayerState(self.bot, new_action)
            else:
                self.states[player_id].action = new_action

    def remove(self, player_ids: List[int]):
        for player_id in player_ids:
            if not self[player_id]:
                continue

            self.states[player_id].action = None
            del self.states[player_id]

class PlayerState:
    def __init__(self, bot: MatchMaker, action: Literal['playing', 'queueing']):
        self.bot = bot

        self._action = None
        self.action  = action

        self.last_updated = utcnow()

    @property
    def action(self):
        return self._action
    
    @action.setter
    def action(self, new_action: Literal['playing', 'queueing']):
        self.bot.dispatch('player_state_update', before=self._action, after=new_action)
        self._action = new_action

        self.last_updated = utcnow()

    @property
    def message(self):
        if self._action == "playing":
            return "are already in a game"
        else:
            return "are already finding a game"