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
        # Regras principais:
        # - Máquina de estados reativa: EXPLORE, COLLECT, CHASE, EVADE, SEARCH.
        # - Coleta: pega blue/red/weak, evita green; marca posição de ouro para planejar rota.
        # - Combate: persegue/atira quando enemy#X; interrompe plano de ouro.
        # - Evasão: ao sofrer dano recua LOS; passos viram SEARCH.
        # - Navegação: evita hazards/bloqueios, penaliza riscos (breeze/flash), prioriza menos visitados.
        # - Planejamento: a cada 100 ações faz A* para ouro conhecido em células seguras visitadas.
        # - Anti-giro: quebra ciclos de viradas forçando andar ou ré quando seguro.
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
        self.turn_streak = 0
        self.last_action: Optional[str] = None
        self.hazard_alert = False  # true when breeze/flash sensed
        self.gold_spots: set[Tuple[int, int]] = set()
        self.powerup_spots: set[Tuple[int, int]] = set()
        self.planned_path: List[str] = []
        self.action_counter = 0
        self.debug = True  # set to False to silence logs
        self.missed_shots = 0
        self._log_buffer: List[str] = []
        self.risky: set[Tuple[int, int]] = set()
        self.message = None  
        self.enemy_seen_last_turn = False

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

    def _is_risky(self, pos: Tuple[int, int]) -> bool:
        return pos in self.risky

    def _mark_blocked_ahead(self):
        self.blocked.add(self._front_pos())

    def _mark_adjacent_risk(self):
        for pos in self.GetObservableAdjacentPositions(self.player):
            self.risky.add(self._pos_tuple(pos))


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
        enemy_found_now = False

        for s in o:
            if s == "blocked":
                self.last_move_failed = True
                self._mark_blocked_ahead()
                self._log("obs: blocked")
            
            elif s == "steps":
                self.heard_steps = 3
                self._log("obs: steps near")
            
            elif s in ("breeze", "flash"):
                # Risco ao redor (poço/teleporte) não bloqueia, mas penaliza caminho
                self._mark_adjacent_risk()
                self.hazard_alert = True
                self._log(f"obs: {s} -> marking adjacent hazard")

            elif s in ("blueLight", "redLight", "weakLight", "greenLight"):
                self.item_here = s
                if s == "greenLight":
                    self.hazards.add(self._pos_tuple(self.player))
                self._log(f"obs: {s} at {self._pos_tuple(self.player)}")
                if s == "blueLight":
                    self.gold_spots.add(self._pos_tuple(self.player))
                elif s == "redLight":
                    self.powerup_spots.add(self._pos_tuple(self.player))

            elif s == "damage":
                # sofre dano: entrar em evasão (LOS)
                self.damage_taken = True
                self.evade_steps = max(self.evade_steps, 3)
                self._log("obs: damage taken, entering evade")

            elif s == "hit":
                # confirmamos tiro acertado
                self.just_hit_enemy = True
                self.missed_shots = 0
                self.message = "Toma essa!" #fala quandoa certa o tiro
                self._log("obs: hit landed")
            
            elif s.startswith("enemy#") or s == "enemy":
                enemy_found_now = True # Marque que vimos alguém
                try:
                    value = s.split("#")[1] if "#" in s else "1"
                    self.enemy_distance = int(value)
                except Exception:
                    self.enemy_distance = 1
                self._log(f"obs: enemy at {self.enemy_distance} steps")
        
        if enemy_found_now and not self.enemy_seen_last_turn:
            self.message = "Achei voce!"

        # Atualiza a memória para o próximo turno
        self.enemy_seen_last_turn = enemy_found_now


    # <summary>
    # No observations received
    # </summary>
    def GetObservationsClean(self):
        self.item_here = None
        self.enemy_distance = None
        self.damage_taken = False
        self.just_hit_enemy = False
        self.last_move_failed = False
        self.hazard_alert = False
        # remove stale gold mark if nothing visível aqui
        if self._pos_tuple(self.player) in self.gold_spots and self.item_here is None:
            self.gold_spots.discard(self._pos_tuple(self.player))
        if self._pos_tuple(self.player) in self.powerup_spots and self.item_here is None:
            self.powerup_spots.discard(self._pos_tuple(self.player))
    

    # <summary>
    # Get Decision
    # </summary>
    # <returns>command string to new decision</returns>
    def GetDecision(self) -> str:
        
        if self.last_action == "atacar":
            if self.just_hit_enemy:
                self.missed_shots = 0  # Acertou! Zera o contador.
            else:
                self.missed_shots += 1 # Errou (bateu na parede/nada), incrementa.
                self._log(f"Tiro falhou! Erros consecutivos: {self.missed_shots}")
        else:
        # Se fizemos qualquer outra coisa (andar, virar), zeramos o contador
            self.missed_shots = 0

        if self.heard_steps > 0:
            self.heard_steps -= 1
        if self.evade_steps > 0:
            self.evade_steps -= 1

        self._update_state()

        if self.state in (AIState.EVADE, AIState.CHASE):
            self.planned_path.clear()

        if self.planned_path:
            decision = self.planned_path.pop(0)
        else:
            if self.energy <= 50:
                self._maybe_plan_to_powerup()
            if not self.planned_path:
                self._maybe_plan_to_gold()
            if self.planned_path:
                decision = self.planned_path.pop(0)
            else:
                if self.state == AIState.EVADE:
                    decision = self._evasive_move()
                elif self.state == AIState.COLLECT:
                    decision = self._collect_decision()
                elif self.state == AIState.CHASE:
                    decision = self._chase_or_attack()
                elif self.state == AIState.SEARCH:
                    decision = self._search_for_enemy()
                else:
                    decision = self._explore_decision()
                    
        if decision == "atacar":
        # Só fala se for o primeiro tiro ou se mudou de ação (para não spammar)
            if self.last_action != "atacar": 
                self.message = "Vou atirar!"

        decision = self._anti_spin(decision)
        self._register_action(decision)
        self._flush_logs(decision)
        return decision

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
        # Regra de coleta: pegar itens úteis, evitar veneno
        if self.item_here == "redLight":
            self.powerup_spots.discard(self._pos_tuple(self.player))
            return "pegar_powerup"
        if self.item_here == "blueLight":
            self.gold_spots.discard(self._pos_tuple(self.player))
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

    # def _chase_or_attack(self) -> str:
    #     # Regras de perseguição/tiro
    #     if self.enemy_distance is not None:
    #         if self.enemy_distance <= 2 or self.just_hit_enemy:
    #             return "atacar"
    #         if self._is_safe(self._front_pos()) and not self.last_move_failed:
    #             return "andar"
    #         return self._pick_turn_by_visit()
    #     return self._search_for_enemy()

    def _chase_or_attack(self) -> str:
        # Regras de perseguição/tiro
        if self.enemy_distance is not None:
            
            if self.missed_shots >= 3:
                self._log("Muitos erros! Tentando reposicionar...")
                return "andar"
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

        if self.hazard_alert and self._is_safe(self._back_pos()) and not self.last_move_failed:
            return "andar_re"

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
                risk = 1 if self._is_risky(pos) else 0
                candidates.append((risk, self.visited.get(pos, 0), priority[action], action))

        if not candidates:
            return self._fallback_move()

        candidates.sort(key=lambda x: (x[0], x[1], x[2]))
        return candidates[0][3]

    def _fallback_move(self) -> str:
        for action, pos in [
            ("virar_esquerda", self._left_pos()),
            ("virar_direita", self._right_pos()),
            ("andar", self._front_pos()),
            ("andar_re", self._back_pos())
        ]:
            if self._is_safe(pos):
                return action
        return "virar_direita"

    def _register_action(self, action: str):
        self.action_counter += 1
        if action in ("virar_esquerda", "virar_direita"):
            self.turn_streak += 1
        else:
            self.turn_streak = 0
        self.last_action = action

    def _anti_spin(self, action: str) -> str:
        # If turning many times, force a move to break loops when safe.
        if action in ("virar_esquerda", "virar_direita"):
            if self.turn_streak >= 2 and self.state in (AIState.EXPLORE, AIState.SEARCH):
                if not self.last_move_failed and self._is_safe(self._front_pos()):
                    return "andar"
                if self._is_safe(self._back_pos()):
                    return "andar_re"
        return action

    def _maybe_plan_to_gold(self):
        if not self.gold_spots:
            return
        if self.action_counter == 0 or self.action_counter % 100 != 0:
            return
        if self.state not in (AIState.EXPLORE, AIState.COLLECT, AIState.SEARCH):
            return
        # Planejamento A*: apenas em células já visitadas e seguras
        start = self._pos_tuple(self.player)
        safe_nodes = {pos for pos in self.visited.keys() if pos not in self.hazards and pos not in self.blocked}
        if start not in safe_nodes:
            safe_nodes.add(start)

        target, path_positions = self._nearest_gold_path(start, safe_nodes)
        if target and path_positions:
            actions = self._path_to_actions(path_positions)
            if actions:
                self.planned_path = actions
                self._log(f"plan: path to gold {target} with {len(actions)} steps")
        
    def _maybe_plan_to_powerup(self):
        # Só planeja se não tiver caminho, se tiver energia baixa e se conhecer algum powerup
        if self.planned_path: 
            return
        if not self.powerup_spots:
            return
            
        # Define quais células são seguras para andar 
        start = self._pos_tuple(self.player)
        safe_nodes = {pos for pos in self.visited.keys() if pos not in self.hazards and pos not in self.blocked}
        if start not in safe_nodes:
            safe_nodes.add(start)

        # Usa a função existente para achar o caminho mais curto
        # Reutilizamos a lógica _nearest_gold_path, mas passamos a lista de powerups
        best_target = None
        best_path = None
        
        # Procura o powerup mais próximo
        for p in self.powerup_spots:
            if p not in safe_nodes:
                continue
            path = self._astar_path(start, p, safe_nodes)
            if path:
                if best_path is None or len(path) < len(best_path):
                    best_path = path
                    best_target = p

        # Se achou um caminho, transforma em ações (andar, virar...)
        if best_target and best_path:
            actions = self._path_to_actions(best_path)
            if actions:
                self.planned_path = actions
                self._log(f"EMERGÊNCIA: Energia {self.energy}%! Buscando powerup em {best_target}")

    def _nearest_gold_path(self, start: Tuple[int, int], safe_nodes: set[Tuple[int, int]]):
        best_target = None
        best_path = None
        for g in self.gold_spots:
            if g not in safe_nodes:
                continue
            path = self._astar_path(start, g, safe_nodes)
            if path:
                if best_path is None or len(path) < len(best_path):
                    best_path = path
                    best_target = g
        return best_target, best_path

    def _astar_path(self, start: Tuple[int, int], goal: Tuple[int, int], safe_nodes: set[Tuple[int, int]]):
        if start == goal:
            return [start]
        open_set = {start}
        came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
        g_score = {start: 0}
        f_score = {start: self._manhattan(start, goal)}
        while open_set:
            current = min(open_set, key=lambda n: f_score.get(n, float("inf")))
            if current == goal:
                return self._reconstruct_path(came_from, current)
            open_set.remove(current)
            for neighbor in self._neighbors(current, safe_nodes):
                tentative_g = g_score[current] + 1
                if tentative_g < g_score.get(neighbor, float("inf")):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + self._manhattan(neighbor, goal)
                    open_set.add(neighbor)
        return None

    def _neighbors(self, pos: Tuple[int, int], safe_nodes: set[Tuple[int, int]]):
        x, y = pos
        candidates = [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]
        return [p for p in candidates if p in safe_nodes]

    def _manhattan(self, a: Tuple[int, int], b: Tuple[int, int]) -> int:
        return abs(a[0]-b[0]) + abs(a[1]-b[1])

    def _reconstruct_path(self, came_from: Dict[Tuple[int, int], Tuple[int, int]], current: Tuple[int, int]):
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path

    def _path_to_actions(self, path: List[Tuple[int, int]]) -> List[str]:
        # path includes start position; convert to actions sequence
        if len(path) < 2:
            return []
        actions: List[str] = []
        dir_sim = self.dir
        current = path[0]
        for nxt in path[1:]:
            dx = nxt[0] - current[0]
            dy = nxt[1] - current[1]
            desired_dir = dir_sim
            if dx == 1:
                desired_dir = "east"
            elif dx == -1:
                desired_dir = "west"
            elif dy == 1:
                desired_dir = "south"
            elif dy == -1:
                desired_dir = "north"

            turn_action, dir_sim = self._turn_actions(dir_sim, desired_dir)
            if turn_action:
                actions.extend(turn_action)
            actions.append("andar")
            current = nxt
        return actions

    def _turn_actions(self, current_dir: str, desired_dir: str):
        if current_dir == desired_dir:
            return [], current_dir
        idx_cur = self._DIRECTIONS.index(current_dir)
        idx_des = self._DIRECTIONS.index(desired_dir)
        diff = (idx_des - idx_cur) % 4
        if diff == 1:
            return ["virar_direita"], desired_dir
        if diff == 3:
            return ["virar_esquerda"], desired_dir
        return ["virar_direita", "virar_direita"], desired_dir

    def _log(self, msg: str):
        if self.debug:
            self._log_buffer.append(msg)

    def _flush_logs(self, decision: str):
        if not self.debug:
            return
        logs = self._log_buffer
        self._log_buffer = []
        if logs:
            print(f"[AI] pos={self._pos_tuple(self.player)} dir={self.dir} state={self.state.name} -> {decision}")
            for m in logs:
                print(f"[AI] {m}")
        else:
            print(f"[AI] pos={self._pos_tuple(self.player)} dir={self.dir} state={self.state.name} -> {decision}")

