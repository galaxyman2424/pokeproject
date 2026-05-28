# Phase 6 — Battle Simulation Framework: Complete

## Overview

Phase 6 builds a battle simulation framework on top of the Pokémon Showdown local server's built-in battle engine. Rather than implementing a custom websocket-based battle client, the phase leverages Showdown's internal `BattleStream` and `RandomPlayerAI` infrastructure directly via a lightweight Node.js subprocess wrapper. Python calls this wrapper via `subprocess` and receives structured JSON results.

---

## Environment

| Property | Value |
| :--- | :--- |
| Operating System | Linux Mint |
| IDE | VSCode |
| Project Location | `~/pokeproject` |
| Python Version | Python 3.12 |
| Virtual Environment | `~/pokeproject/venv` |
| Node.js Version | v18.19.1 |
| Showdown Server | `~/pokemon-showdown` (local clone) |

**New Python dependency:**
```
websockets  (installed but unused — superseded by subprocess approach)
```

---

## Project File Structure

```
~/pokeproject/
├── venv/
├── raw_logs/
├── etl/
│   ├── extract.py
│   ├── transform.py
│   └── load.py
├── analysis/
│   ├── __init__.py
│   ├── usage_analysis.py
│   ├── export.py
│   ├── co_occurrence.py
│   ├── pokemon_data.py
│   ├── team_features.py
│   └── threat_analysis.py
├── simulation/
│   ├── __init__.py
│   ├── showdown_client.py     # packed team format helpers (build/parse)
│   ├── set_completion.py      # fills partial movesets to full legal sets
│   ├── battle_agent.py        # greedy type-effectiveness agent (reference)
│   ├── simulation_runner.py   # primary simulation interface
│   └── test_connection.py     # smoke test
├── data/
│   ├── pokedex.json
│   └── typechart.json
├── output/
│   └── ...
├── db/
│   └── schema.sql
├── config.py
├── main.py
└── .gitignore

~/pokemon-showdown/
└── dist/sim/tools/
    └── battle-runner.js       # Node.js battle engine wrapper
```

---

## Architecture Decision — Subprocess over Websocket

The initial design called for two Python websocket clients connecting to a local Showdown server instance, exchanging challenges, and driving battles via the Showdown protocol. During implementation this approach hit a series of blocking issues:

- The `/trn` login command requires waiting for `|updateuser|` confirmation before sending any further commands, creating async sequencing complexity
- Battle room assignment (`|init|`) arrives tagged with the room ID before any handler is registered for that room, requiring a wildcard dispatch mechanism
- The overall approach added ~150 lines of connection and protocol management code for no analytical benefit

The Showdown repository contains a complete in-process battle engine (`BattleStream`, `getPlayerStreams`, `RandomPlayerAI`) used for its own test suite. This engine runs battles entirely in memory with no networking required. A thin Node.js wrapper script (`battle-runner.js`) exposes this engine to Python via stdin/stdout, accepting two packed team strings and a battle count as CLI arguments and printing a JSON result.

This approach is:
- **Simpler** — ~40 lines of Node.js vs ~300 lines of async websocket code
- **Faster** — no network overhead, no login handshake, no room assignment
- **More reliable** — no connection state, no timeouts, no auth issues
- **Scalable** — trivially parallelizable via multiple subprocesses

---

## Components

### battle-runner.js (`~/pokemon-showdown/dist/sim/tools/`)

Node.js script that wraps the Showdown battle engine. Accepts two packed team strings and a battle count as CLI arguments, runs N battles using `RandomPlayerAI` for both sides, and prints a single JSON object to stdout.

```javascript
node battle-runner.js "<packed_team_a>" "<packed_team_b>" <n_battles>
// stdout: {"team_a_wins":3,"team_b_wins":2,"ties":0,"win_rate":0.6,"battles":5}
```

Uses `gen9ou` format. The `RandomPlayerAI` makes legal random move choices each turn — a baseline agent sufficient for relative team strength estimation.

---

### set_completion.py

Fills partial Pokémon sets (as observed in replay data) to complete legal 4-move sets ready for simulation.

**Move completion** — pulls the most-used moves for each species from `output/move_usage.csv` (Phase 2 data). Known moves from replay data take priority; remaining slots filled by usage rank. Falls back to `Tackle` if insufficient data.

**Item completion** — checks `output/item_usage.csv` first (minimum 3 observations required). Falls back to a hardcoded `ITEM_DEFAULTS` dict covering all top OU Pokémon. Final fallback: `Leftovers`.

**EV spreads and natures** — inferred from base stats. Fast Pokémon (base Speed ≥ 80) with higher Attack than Sp. Atk get `252 Atk / 252 Spe Jolly`. Fast special attackers get `252 SpA / 252 Spe Timid`. Slow physical/special Pokémon get 252/252 bulk spreads.

**Ability and Tera type** — populated from hardcoded override dicts covering all common OU Pokémon. Falls back to first ability from `pokedex.json` and `Normal` tera.

---

### simulation_runner.py

Primary Python interface for Phase 5. Two public functions:

**`simulate_matchup(team_a, team_b, n_battles, ...)`** — runs N battles between two teams. Calls `set_completion.complete_team()` to build full sets, `build_packed_team()` to serialize, then invokes `battle-runner.js` via `subprocess.run()`. Returns:

```python
{
    "team_a_wins": int,
    "team_b_wins": int,
    "ties":        int,
    "win_rate":    float,   # team_a win rate 0.0–1.0
    "battles":     int,
}
```

**`simulate_vs_meta(team, meta_teams, n_battles_per_matchup, ...)`** — evaluates a team against a list of opponent teams. Calls `simulate_matchup` for each matchup and aggregates results into an overall win rate. Used by Phase 5 fitness evaluation.

---

### showdown_client.py

Retained for its packed team format helpers:

**`build_packed_team(sets)`** — converts a list of set dicts to Showdown's `]`-delimited packed format string.

**`parse_packed_team(packed)`** — reverse operation. Both are used by the simulation runner and will be used by Phase 5 when generating and serializing candidate teams.

---

### battle_agent.py

A Python greedy type-effectiveness agent written during the websocket phase. Not used in the current subprocess architecture (the Node.js `RandomPlayerAI` handles decision-making), but retained as a reference implementation and potential foundation for a future TypeScript agent that subclasses `RandomPlayerAI` with type-aware move selection.

---

## Validation

**Smoke test results (`simulation/test_connection.py`):**

| Test | Result |
| :--- | :--- |
| Set completion — 6 Pokémon complete sets | PASS |
| Packed team format — 882 char string, correct structure | PASS |
| Websocket connection (retained, unused) | PASS |
| Subprocess simulation — 3 battles, JSON output | PASS |

**Sample simulation result:**

```
Team A: Great Tusk / Gholdengo / Kingambit / Dragonite / Hatterene / Corviknight
Team B: Pelipper / Kingdra / Araquanid / Iron Valiant / Great Tusk / Gholdengo
Battles: 5
Result: {'team_a_wins': 3, 'team_b_wins': 2, 'ties': 0, 'win_rate': 0.6, 'battles': 5}
```

Rain team (Team B) is competitive against the balance core (Team A), consistent with Phase 4's `weak_to_rain: YES` finding for this team composition.

---

## Performance

A 5-battle simulation completes in approximately 1–2 seconds. At this rate:

| Battles | Estimated Time |
| :--- | :--- |
| 10 | ~3s |
| 50 | ~15s |
| 100 | ~30s |
| 500 | ~2.5min |

For Phase 5's genetic algorithm fitness evaluation, 10–20 battles per team per generation is a reasonable budget. A population of 50 teams evaluated at 10 battles each = 500 battles ≈ 2.5 minutes per generation. Parallelizing subprocess calls via `concurrent.futures.ProcessPoolExecutor` can reduce this significantly and will be implemented in Phase 5 if generation time is a bottleneck.

---

## Phase 6 Deliverable

A complete battle simulation framework that:

- Runs full Gen 9 OU battles using the Showdown battle engine in-process
- Completes partial replay movesets to full legal competitive sets
- Serializes teams to Showdown's packed format for simulation input
- Returns structured win rate statistics as Python dicts
- Supports both head-to-head matchup evaluation and meta-wide evaluation
- Executes 5 battles in ~1-2 seconds with no external server dependency
- Exposes `simulate_matchup()` and `simulate_vs_meta()` as clean interfaces for Phase 5 fitness evaluation
