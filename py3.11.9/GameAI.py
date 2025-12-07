#!/usr/bin/env python

"""GameAI.py: INF1771 GameAI File - Where Decisions are made."""
#############################################################
#Copyright 2020 Augusto Baffa
#
#Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
#The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
#############################################################
__author__      = "Augusto Baffa"
__copyright__   = "Copyright 2020, Rio de janeiro, Brazil"
__license__ = "GPL"
__version__ = "1.0.0"
__email__ = "abaffa@inf.puc-rio.br"
#############################################################

from Map.Position import Position
from enum import Enum
from typing import List, Dict, Optional, Tuple

# <summary>
# Game AI Example
# </summary>
class AIState(Enum):
    EXPLORE = 0
    COLLECT = 1
    CHASE = 2
    EVADE = 3
    SEARCH = 4

class GameAI():

    def __init__(self):
        self.player = Position()
        self.state = AIState.EXPLORE
        self.dir = "north"
        self.score = 0
        self.energy = 0
        self.external_state = ""

        self.visited: Dict[Tuple[int, int], int] = {}
        self.hazards: set[Tuple[int, int]] = set()
        self.blocked: set[Tuple[int, int]] = set()

        self.item_here: Optional[str] = None
        self.enemy_distance: Optional[int] = None
        self.heard_steps = 0
        self.damage_taken = False
        self.just_hit_enemy = False
        self.last_move_failed = False
        self.evade_steps = 0
        self.turn_bias = 0  # alternates left/right when searching

    # <summary>
    # Refresh player status
    # </summary>
    # <param name="x">player position x</param>
    # <param name="y">player position y</param>
    # <param name="dir">player direction</param>
    # <param name="state">player state</param>
    # <param name="score">player score</param>
    # <param name="energy">player energy</param>
    def SetStatus(self, x: int, y: int, dir: str, state: str, score: int, energy: int):
        
        self.SetPlayerPosition(x, y)
        self.dir = dir.lower()

        self.external_state = state
        self.score = score
        self.energy = energy
        self._mark_visit()

    _DIRECTIONS = ["north", "east", "south", "west"]

    def _pos_tuple(self, pos: Position) -> Tuple[int, int]:
        return (pos.x, pos.y)

    def _mark_visit(self):
        pos = self._pos_tuple(self.player)
        self.visited[pos] = self.visited.get(pos, 0) + 1

    def _direction_after_turn(self, turn: str) -> str:
        idx = self._DIRECTIONS.index(self.dir)
        if turn == "left":
            idx = (idx - 1) % 4
        elif turn == "right":
            idx = (idx + 1) % 4
        elif turn == "back":
            idx = (idx + 2) % 4
        return self._DIRECTIONS[idx]

    def _pos_in_direction(self, direction: str, steps: int = 1) -> Tuple[int, int]:
        if direction == "north":
            return (self.player.x, self.player.y - steps)
        if direction == "east":
            return (self.player.x + steps, self.player.y)
        if direction == "south":
            return (self.player.x, self.player.y + steps)
        return (self.player.x - steps, self.player.y)

    def _front_pos(self) -> Tuple[int, int]:
        return self._pos_in_direction(self.dir, 1)

    def _back_pos(self) -> Tuple[int, int]:
        return self._pos_in_direction(self._direction_after_turn("back"), 1)

    def _left_pos(self) -> Tuple[int, int]:
        return self._pos_in_direction(self._direction_after_turn("left"), 1)

    def _right_pos(self) -> Tuple[int, int]:
        return self._pos_in_direction(self._direction_after_turn("right"), 1)

    def _is_safe(self, pos: Tuple[int, int]) -> bool:
        return pos not in self.hazards and pos not in self.blocked

    def _mark_blocked_ahead(self):
        self.blocked.add(self._front_pos())

    def _mark_adjacent_hazard(self):
        for pos in self.GetObservableAdjacentPositions(self.player):
            self.hazards.add(self._pos_tuple(pos))


    # <summary>
    # Get list of observable adjacent positions
    # </summary>
    # <returns>List of observable adjacent positions</returns>
    def GetCurrentObservableAdjacentPositions(self) -> List[Position]:
        return self.GetObservableAdjacentPositions(self.player)
        
    def GetObservableAdjacentPositions(self, pos):
        ret = []

        ret.append(Position(pos.x - 1, pos.y))
        ret.append(Position(pos.x + 1, pos.y))
        ret.append(Position(pos.x, pos.y - 1))
        ret.append(Position(pos.x, pos.y + 1))

        return ret


    # <summary>
    # Get list of all adjacent positions (including diagonal)
    # </summary>
    # <returns>List of all adjacent positions (including diagonal)</returns>
    def GetAllAdjacentPositions(self):
    
        ret = []

        ret.append(Position(self.player.x - 1, self.player.y - 1))
        ret.append(Position(self.player.x, self.player.y - 1))
        ret.append(Position(self.player.x + 1, self.player.y - 1))

        ret.append(Position(self.player.x - 1, self.player.y))
        ret.append(Position(self.player.x + 1, self.player.y))

        ret.append(Position(self.player.x - 1, self.player.y + 1))
        ret.append(Position(self.player.x, self.player.y + 1))
        ret.append(Position(self.player.x + 1, self.player.y + 1))

        return ret

    def NextPositionAhead(self, steps):
        pos = self._pos_in_direction(self.dir, steps)
        return Position(pos[0], pos[1])

    # <summary>
    # Get next forward position
    # </summary>
    # <returns>next forward position</returns>
    def NextPosition(self) -> Position:
        return self.NextPositionAhead(1)
    

    # <summary>
    # Player position
    # </summary>
    # <returns>player position</returns>
    def GetPlayerPosition(self):
        return Position(self.player.x, self.player.y)


    # <summary>
    # Set player position
    # </summary>
    # <param name="x">x position</param>
    # <param name="y">y position</param>
    def SetPlayerPosition(self, x: int, y: int):
        self.player.x = x
        self.player.y = y
    

    # <summary>
    # Observations received
    # </summary>
    # <param name="o">list of observations</param>
    def GetObservations(self, o):
        for s in o:
            if s == "blocked":
                self.last_move_failed = True
                self._mark_blocked_ahead()
            
            elif s == "steps":
                self.heard_steps = 3
            
            elif s in ("breeze", "flash"):
                self._mark_adjacent_hazard()

            elif s in ("blueLight", "redLight", "weakLight", "greenLight"):
                self.item_here = s
                if s == "greenLight":
                    self.hazards.add(self._pos_tuple(self.player))

            elif s == "damage":
                self.damage_taken = True
                self.evade_steps = max(self.evade_steps, 3)

            elif s == "hit":
                self.just_hit_enemy = True
            
            elif s.startswith("enemy#") or s == "enemy":
                try:
                    value = s.split("#")[1] if "#" in s else "1"
                    self.enemy_distance = int(value)
                except Exception:
                    self.enemy_distance = 1


    # <summary>
    # No observations received
    # </summary>
    def GetObservationsClean(self):
        self.item_here = None
        self.enemy_distance = None
        self.damage_taken = False
        self.just_hit_enemy = False
        self.last_move_failed = False
    

    # <summary>
    # Get Decision
    # </summary>
    # <returns>command string to new decision</returns>
    def GetDecision(self) -> str:

        if self.heard_steps > 0:
            self.heard_steps -= 1
        if self.evade_steps > 0:
            self.evade_steps -= 1

        self._update_state()

        if self.state == AIState.EVADE:
            return self._evasive_move()
        if self.state == AIState.COLLECT:
            return self._collect_decision()
        if self.state == AIState.CHASE:
            return self._chase_or_attack()
        if self.state == AIState.SEARCH:
            return self._search_for_enemy()

        return self._explore_decision()

    def _update_state(self):
        if self.damage_taken or self.evade_steps > 0:
            self.state = AIState.EVADE
            return

        if self.item_here in ("blueLight", "redLight", "weakLight"):
            self.state = AIState.COLLECT
            return

        if self.enemy_distance is not None:
            self.state = AIState.CHASE
            return

        if self.heard_steps > 0:
            self.state = AIState.SEARCH
            return

        self.state = AIState.EXPLORE

    def _collect_decision(self) -> str:
        if self.item_here == "redLight":
            return "pegar_powerup"
        if self.item_here == "blueLight":
            return "pegar_ouro"
        if self.item_here == "weakLight":
            return "pegar_anel"
        # avoid pegar quando greenLight (veneno)
        return "virar_direita"

    def _evasive_move(self) -> str:
        # priority: break line of sight and leave current tile
        if self._is_safe(self._back_pos()):
            return "andar_re"

        left_safe = self._is_safe(self._left_pos())
        right_safe = self._is_safe(self._right_pos())
        if left_safe and right_safe:
            return "virar_esquerda" if self.turn_bias % 2 == 0 else "virar_direita"
        if left_safe:
            return "virar_esquerda"
        if right_safe:
            return "virar_direita"

        if not self.last_move_failed and self._is_safe(self._front_pos()):
            return "andar"

        return "virar_direita"

    def _chase_or_attack(self) -> str:
        if self.enemy_distance is not None:
            if self.enemy_distance <= 2 or self.just_hit_enemy:
                return "atacar"
            if self._is_safe(self._front_pos()) and not self.last_move_failed:
                return "andar"
            return self._pick_turn_by_visit()
        return self._search_for_enemy()

    def _search_for_enemy(self) -> str:
        self.turn_bias ^= 1
        # rotate to scan while keeping movement cost low
        if self.turn_bias % 2 == 0:
            return "virar_esquerda"
        return "virar_direita"

    def _explore_decision(self) -> str:
        forward_pos = self._front_pos()
        if self.last_move_failed or not self._is_safe(forward_pos):
            return self._pick_turn_by_visit()

        return self._pick_direction_by_visit()

    def _pick_turn_by_visit(self) -> str:
        left_pos = self._left_pos()
        right_pos = self._right_pos()
        options = []

        if self._is_safe(left_pos):
            options.append((self.visited.get(left_pos, 0), "virar_esquerda"))
        if self._is_safe(right_pos):
            options.append((self.visited.get(right_pos, 0), "virar_direita"))

        if not options:
            return self._fallback_move()

        options.sort(key=lambda x: x[0])
        return options[0][1]

    def _pick_direction_by_visit(self) -> str:
        priority = {"andar": 0, "virar_esquerda": 1, "virar_direita": 2, "andar_re": 3}
        candidates = []

        mapping = [
            ("andar", self._front_pos()),
            ("virar_esquerda", self._left_pos()),
            ("virar_direita", self._right_pos()),
            ("andar_re", self._back_pos())
        ]

        for action, pos in mapping:
            if self._is_safe(pos):
                candidates.append((self.visited.get(pos, 0), priority[action], action))

        if not candidates:
            return self._fallback_move()

        candidates.sort(key=lambda x: (x[0], x[1]))
        return candidates[0][2]

    def _fallback_move(self) -> str:
        for action, pos in [
            ("virar_esquerda", self._left_pos()),
            ("virar_direita", self._right_pos()),
            ("andar", self._front_pos()),
            ("andar_re", self._back_pos())
        ]:
            if pos not in self.blocked:
                return action
        return "virar_direita"

