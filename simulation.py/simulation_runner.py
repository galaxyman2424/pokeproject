"""
simulation/simulation_runner.py

Runs N battles between two teams on the local Showdown server and returns
win rate statistics. This is the primary interface Phase 5 will call into
for fitness evaluation.

Architecture:
- Two ShowdownClient instances connect as PokeBot1 and PokeBot2
- PokeBot1 challenges PokeBot2
- Both clients run BattleAgents that respond to Showdown's |request| messages
- Results are logged and aggregated

Usage:
    from simulation.simulation_runner import simulate_matchup

    result = await simulate_matchup(
        team_a=["Great Tusk", "Gholdengo", "Kingambit", "Dragonite", "Hatterene", "Corviknight"],
        team_b=["Pelipper", "Kingdra", "Araquanid", "Iron Valiant", "Great Tusk", "Gholdengo"],
        n_battles=20,
    )
    print(result)
    # {"team_a_wins": 13, "team_b_wins": 7, "win_rate": 0.65, "battles": 20}
"""

import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from simulation.showdown_client import ShowdownClient, build_packed_team
from simulation.set_completion import complete_team
from simulation.battle_agent import BattleAgent
from analysis.pokemon_data import get_types


FORMAT = "gen9ou"
BOT1   = "PokeBot1"
BOT2   = "PokeBot2"


# ──────────────────────────────────────────────────────────────────────────────
# Battle session — manages one battle between two agents
# ──────────────────────────────────────────────────────────────────────────────

class BattleSession:
    """
    Manages a single battle between two BattleAgents via two ShowdownClients.
    Listens to the Showdown message stream and drives both agents.
    """

    def __init__(
        self,
        client1: ShowdownClient,
        client2: ShowdownClient,
        agent1:  BattleAgent,
        agent2:  BattleAgent,
        timeout: float = 120.0,
    ):
        self.client1  = client1
        self.client2  = client2
        self.agent1   = agent1
        self.agent2   = agent2
        self.timeout  = timeout
        self.room_id  = None
        self.winner   = None  # "p1" or "p2" or None (timeout)
        self._done    = asyncio.Event()

        # Track active opponent types for each agent's decisions
        self._opponent_types = {"p1": ["Normal"], "p2": ["Normal"]}

        # Latest |request| state per player
        self._request = {"p1": None, "p2": None}

    async def run(self, room_id: str):
        self.room_id = room_id
        self.client1.register_handler(room_id, self._handle_message)
        self.client2.register_handler(room_id, self._handle_message)

        try:
            await asyncio.wait_for(self._done.wait(), timeout=self.timeout)
        except asyncio.TimeoutError:
            print(f"[session] Battle {room_id} timed out")
            self.winner = None
        finally:
            self.client1.unregister_handler(room_id)
            self.client2.unregister_handler(room_id)

    async def _handle_message(self, room: str, lines: list[tuple[str, str]]):
        """Dispatch Showdown room messages to the appropriate handler."""
        for tag, rest in lines:
            await self._dispatch(tag, rest)

    async def _dispatch(self, tag: str, rest: str):
        parts = rest.split("|")

        if tag == "win":
            winner_name = rest.strip()
            if winner_name == BOT1:
                self.winner = "p1"
            else:
                self.winner = "p2"
            self._done.set()

        elif tag == "tie":
            self.winner = None
            self._done.set()

        elif tag == "switch":
            # |switch|p1a: Great Tusk|Great Tusk, L100|100/100
            actor_raw = parts[0] if parts else ""
            pid = actor_raw[:2]
            species_raw = parts[1] if len(parts) > 1 else ""
            species = species_raw.split(",")[0].strip()

            agent = self.agent1 if pid == "p1" else self.agent2
            agent.handle_switch(species)

            # Update opponent type knowledge for the other agent
            opp_pid = "p2" if pid == "p1" else "p1"
            self._opponent_types[opp_pid] = get_types(species) or ["Normal"]

        elif tag == "faint":
            # |faint|p1a: Great Tusk
            actor_raw = parts[0] if parts else ""
            pid = actor_raw[:2]
            species_raw = parts[0][4:].strip() if len(parts[0]) > 4 else ""
            agent = self.agent1 if pid == "p1" else self.agent2
            agent.handle_faint(species_raw)

        elif tag == "request":
            # |request|{json}
            if not rest:
                return
            try:
                req = json.loads(rest)
            except json.JSONDecodeError:
                return

            pid = "p1" if self.client1.username == BOT1 else "p2"
            # Determine which client received this request
            # Both clients see the same room stream but requests are player-specific
            # We handle by tracking separately via the client reference in the handler
            # For simplicity: p1's client receives p1 requests, p2's receives p2 requests
            # This is routed correctly because each client is registered separately

            await self._handle_request(req)

    async def _handle_request(self, req: dict):
        """
        Process a |request| message and send a response.
        The request tells us which moves and switches are available.
        """
        if req.get("wait"):
            return

        # Determine which side this request is for based on the side field
        side = req.get("side", {})
        pid  = side.get("id", "p1")   # "p1" or "p2"

        agent  = self.agent1 if pid == "p1" else self.agent2
        client = self.client1 if pid == "p1" else self.client2

        # Forced switch (active fainted)
        if req.get("forceSwitch"):
            slot_type, slot = agent.forced_switch()
            await client.send_room(self.room_id, f"/choose {slot_type} {slot}")
            return

        # Normal turn
        active_data = req.get("active", [{}])
        if not active_data:
            return
        moves_data = active_data[0].get("moves", [])
        available_moves = [
            m["move"] for m in moves_data
            if not m.get("disabled", False)
        ]

        opp_pid = "p2" if pid == "p1" else "p1"
        opp_types = self._opponent_types.get(opp_pid, ["Normal"])

        action_type, slot = agent.choose_move(available_moves, opp_types)
        await client.send_room(self.room_id, f"/choose {action_type} {slot}")


# ──────────────────────────────────────────────────────────────────────────────
# Simulation runner
# ──────────────────────────────────────────────────────────────────────────────

async def _run_single_battle(
    client1: ShowdownClient,
    client2: ShowdownClient,
    sets_a:  list[dict],
    sets_b:  list[dict],
    battle_num: int,
) -> str | None:
    """Run a single battle. Returns 'p1', 'p2', or None (timeout/tie)."""

    packed_a = build_packed_team(sets_a)
    packed_b = build_packed_team(sets_b)

    agent1 = BattleAgent("p1", sets_a)
    agent2 = BattleAgent("p2", sets_b)

    # Wait for the battle room to be assigned
    room_event = asyncio.Event()
    room_id_holder = {}

    original_handler = client1.room_handlers.copy()

    async def lobby_handler(room: str, lines: list):
        for tag, rest in lines:
            if tag == "init" and "battle" in room:
                room_id_holder["room"] = room
                room_event.set()

    # Register a temporary global handler to catch the room init
    client1.room_handlers[""] = lobby_handler

    await client1.challenge_user(BOT2, FORMAT, packed_a)
    await asyncio.sleep(0.5)
    await client2.accept_challenge(BOT1, packed_b)

    try:
        await asyncio.wait_for(room_event.wait(), timeout=15.0)
    except asyncio.TimeoutError:
        print(f"[runner] Battle {battle_num}: room assignment timed out")
        client1.room_handlers.pop("", None)
        return None

    room_id = room_id_holder["room"]
    client1.room_handlers.pop("", None)

    print(f"[runner] Battle {battle_num}: room {room_id}")

    session = BattleSession(client1, client2, agent1, agent2)
    await session.run(room_id)

    return session.winner


async def simulate_matchup(
    team_a: list[str],
    team_b: list[str],
    n_battles: int = 20,
    movesets_a: dict | None = None,
    movesets_b: dict | None = None,
    verbose: bool = True,
) -> dict:
    """
    Simulate N battles between team_a and team_b.

    Args:
        team_a:      List of 6 Pokémon names for team A
        team_b:      List of 6 Pokémon names for team B
        n_battles:   Number of battles to simulate
        movesets_a:  Optional partial moveset data for team A (from replay DB)
        movesets_b:  Optional partial moveset data for team B
        verbose:     Print progress

    Returns:
        {
            "team_a_wins": int,
            "team_b_wins": int,
            "ties":        int,
            "win_rate":    float,   # team_a win rate (0.0–1.0)
            "battles":     int,
        }
    """
    sets_a = complete_team(team_a, movesets_a)
    sets_b = complete_team(team_b, movesets_b)

    client1 = ShowdownClient(BOT1)
    client2 = ShowdownClient(BOT2)

    await client1.connect()
    await client2.connect()

    wins_a = 0
    wins_b = 0
    ties   = 0

    for i in range(1, n_battles + 1):
        winner = await _run_single_battle(client1, client2, sets_a, sets_b, i)
        if winner == "p1":
            wins_a += 1
        elif winner == "p2":
            wins_b += 1
        else:
            ties += 1

        if verbose:
            print(f"[runner] Battle {i}/{n_battles} → winner: {winner or 'tie/timeout'} | A: {wins_a} B: {wins_b}")

        # Small delay between battles to avoid overwhelming the server
        await asyncio.sleep(1.0)

    await client1.disconnect()
    await client2.disconnect()

    completed = wins_a + wins_b
    win_rate  = wins_a / completed if completed > 0 else 0.0

    result = {
        "team_a_wins": wins_a,
        "team_b_wins": wins_b,
        "ties":        ties,
        "win_rate":    round(win_rate, 4),
        "battles":     n_battles,
    }

    if verbose:
        print(f"\n[runner] Results: {result}")

    return result


async def simulate_vs_meta(
    team: list[str],
    meta_teams: list[list[str]],
    n_battles_per_matchup: int = 10,
    movesets: dict | None = None,
    verbose: bool = True,
) -> dict:
    """
    Simulate a team against a list of meta teams and compute overall win rate.
    Used by Phase 5 to evaluate generated teams against the metagame distribution.

    Args:
        team:                   The team being evaluated
        meta_teams:             List of opponent teams sampled from meta
        n_battles_per_matchup:  Battles per matchup
        movesets:               Optional moveset data for the evaluated team

    Returns:
        {
            "overall_win_rate": float,
            "matchup_results":  list of per-matchup result dicts,
            "total_battles":    int,
        }
    """
    matchup_results = []
    total_wins = 0
    total_battles = 0

    for i, opponent in enumerate(meta_teams):
        if verbose:
            print(f"\n[meta_sim] Matchup {i+1}/{len(meta_teams)}: vs {opponent[:3]}...")
        result = await simulate_matchup(
            team_a=team,
            team_b=opponent,
            n_battles=n_battles_per_matchup,
            movesets_a=movesets,
            verbose=False,
        )
        matchup_results.append({"opponent": opponent, **result})
        total_wins   += result["team_a_wins"]
        total_battles += result["battles"]

    overall_win_rate = total_wins / total_battles if total_battles > 0 else 0.0

    return {
        "overall_win_rate": round(overall_win_rate, 4),
        "matchup_results":  matchup_results,
        "total_battles":    total_battles,
    }


# ──────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    TEAM_A = ["Great Tusk", "Gholdengo", "Kingambit", "Dragonite", "Hatterene", "Corviknight"]
    TEAM_B = ["Pelipper", "Kingdra", "Araquanid", "Iron Valiant", "Great Tusk", "Gholdengo"]

    result = asyncio.run(simulate_matchup(TEAM_A, TEAM_B, n_battles=5))
    print(result)