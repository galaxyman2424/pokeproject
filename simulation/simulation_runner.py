"""
simulation/simulation_runner.py

Runs N battles between two teams via the local Showdown battle engine.
Calls the Node.js battle-runner.js script via subprocess — no websockets needed.

Usage:
    from simulation.simulation_runner import simulate_matchup
    result = asyncio.run(simulate_matchup(team_a, team_b, n_battles=20))
"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from simulation.set_completion import complete_team
from simulation.showdown_client import build_packed_team

BATTLE_RUNNER = Path.home() / "pokemon-showdown/dist/sim/tools/battle-runner.js"


def simulate_matchup(
    team_a: list[str],
    team_b: list[str],
    n_battles: int = 20,
    movesets_a: dict | None = None,
    movesets_b: dict | None = None,
    verbose: bool = True,
) -> dict:
    sets_a = complete_team(team_a, movesets_a)
    sets_b = complete_team(team_b, movesets_b)
    packed_a = build_packed_team(sets_a)
    packed_b = build_packed_team(sets_b)

    if verbose:
        print(f"[sim] {team_a[:3]}... vs {team_b[:3]}... ({n_battles} battles)")

    result = subprocess.run(
        ["node", str(BATTLE_RUNNER), packed_a, packed_b, str(n_battles)],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"battle-runner failed: {result.stderr}")

    data = json.loads(result.stdout.strip().splitlines()[-1])

    if verbose:
        print(f"[sim] Result: {data}")

    return data


def simulate_vs_meta(
    team: list[str],
    meta_teams: list[list[str]],
    n_battles_per_matchup: int = 10,
    movesets: dict | None = None,
    verbose: bool = True,
) -> dict:
    total_wins = 0
    total_battles = 0
    matchup_results = []

    for i, opponent in enumerate(meta_teams):
        if verbose:
            print(f"\n[meta_sim] Matchup {i+1}/{len(meta_teams)}")
        result = simulate_matchup(
            team_a=team,
            team_b=opponent,
            n_battles=n_battles_per_matchup,
            movesets_a=movesets,
            verbose=False,
        )
        matchup_results.append({"opponent": opponent, **result})
        total_wins    += result["team_a_wins"]
        total_battles += result["battles"]

    overall_win_rate = total_wins / total_battles if total_battles > 0 else 0.0

    return {
        "overall_win_rate": round(overall_win_rate, 4),
        "matchup_results":  matchup_results,
        "total_battles":    total_battles,
    }


if __name__ == "__main__":
    TEAM_A = ["Great Tusk", "Gholdengo", "Kingambit", "Dragonite", "Hatterene", "Corviknight"]
    TEAM_B = ["Pelipper", "Kingdra", "Araquanid", "Iron Valiant", "Great Tusk", "Gholdengo"]
    result = simulate_matchup(TEAM_A, TEAM_B, n_battles=5)
    print(result)