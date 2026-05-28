"""
simulation/test_connection.py

Smoke test for the simulation stack. Run this before attempting full simulations.

Tests in order:
1. set_completion — can we build complete sets from the Phase 2 data?
2. build_packed_team — does the packed format string look correct?
3. ShowdownClient connection — can we connect and log in to the local server?
4. Single 1-battle simulation — does a full battle run end-to-end?

Run with:
    cd ~/pokeproject
    python3 simulation/test_connection.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from simulation.set_completion import complete_team
from simulation.showdown_client import ShowdownClient, build_packed_team
from simulation.simulation_runner import simulate_matchup


TEAM_A = ["Great Tusk", "Gholdengo", "Kingambit", "Dragonite", "Hatterene", "Corviknight"]
TEAM_B = ["Pelipper", "Kingdra", "Araquanid", "Iron Valiant", "Great Tusk", "Gholdengo"]


# ── Test 1: Set completion ────────────────────────────────────────────────────

def test_set_completion():
    print("\n── Test 1: Set completion ──")
    sets = complete_team(TEAM_A)
    assert len(sets) == 6, f"Expected 6 sets, got {len(sets)}"
    for s in sets:
        assert len(s["moves"]) == 4, f"{s['name']} has {len(s['moves'])} moves, expected 4"
        assert s["item"],           f"{s['name']} has no item"
        assert s["ability"],        f"{s['name']} has no ability"
        print(f"  {s['name']:22} | {s['item']:25} | {s['ability']:22} | {', '.join(s['moves'])}")
    print("  PASS")


# ── Test 2: Packed team format ────────────────────────────────────────────────

def test_packed_team():
    print("\n── Test 2: Packed team format ──")
    sets   = complete_team(TEAM_A)
    packed = build_packed_team(sets)
    mons   = packed.split("]")
    assert len(mons) == 6, f"Expected 6 packed mons, got {len(mons)}"
    print(f"  Packed string length: {len(packed)} chars")
    print(f"  First mon: {mons[0][:80]}...")
    print("  PASS")


# ── Test 3: Websocket connection ──────────────────────────────────────────────

async def test_connection():
    print("\n── Test 3: Websocket connection ──")
    client = ShowdownClient("PokeBotTest")
    try:
        await client.connect()
        print("  Connected and logged in successfully")
        await asyncio.sleep(1)
        print("  PASS")
    except Exception as e:
        print(f"  FAIL: {e}")
        print("  Is the Showdown server running? Start it with:")
        print("    cd ~/pokemon-showdown && node pokemon-showdown start --no-security")
        raise
    finally:
        await client.disconnect()


# ── Test 4: Single battle ─────────────────────────────────────────────────────

# ── Test 4: Simulation via subprocess ────────────────────────────────────────

def test_simulation():
    print("\n── Test 4: Simulation via subprocess ──")
    print(f"  Team A: {TEAM_A[:3]}...")
    print(f"  Team B: {TEAM_B[:3]}...")
    from simulation.simulation_runner import simulate_matchup
    result = simulate_matchup(TEAM_A, TEAM_B, n_battles=3, verbose=False)
    assert result["battles"] == 3
    assert result["team_a_wins"] + result["team_b_wins"] + result["ties"] == 3
    print(f"  Result: {result}")
    print("  PASS")

# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    print("=" * 60)
    print("  PokéMeta Simulation Stack — Smoke Test")
    print("=" * 60)

    # Tests 1 and 2 are synchronous
    test_set_completion()
    test_packed_team()

    # Tests 3 and 4 require the server
    await test_connection()
    await test_single_battle()

    print("\n" + "=" * 60)
    print("  All tests passed. Simulation stack is ready.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())