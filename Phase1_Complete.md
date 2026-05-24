# Phase 1 — Data Collection and Replay Parsing: Complete

## Overview

Phase 1 establishes the foundational data infrastructure for the PokéMeta system. A full ETL (Extract, Transform, Load) pipeline was designed and implemented from scratch to download real competitive Pokémon battle replays from Pokémon Showdown, parse them into structured relational data, and persist them into a PostgreSQL database. The pipeline is idempotent — it can be re-run at any time to ingest new replays without creating duplicate records.

---

## Environment

| Property | Value |
| :--- | :--- |
| Operating System | Linux Mint |
| IDE | VSCode |
| Project Location | `~/pokeproject` |
| Python Version | Python 3.12 |
| Virtual Environment | `~/pokeproject/venv` (python3.12-venv) |
| Version Control | Git — pushed to `github.com/galaxyman2424/pokeproject` |

**Dependencies installed:**
```
requests
pandas
psycopg2-binary
```

---

## Project File Structure

```
~/pokeproject/
├── venv/                  # Python virtual environment
├── raw_logs/              # Downloaded .log files from Pokémon Showdown
├── etl/
│   ├── extract.py         # E — Downloads raw replay logs
│   ├── transform.py       # T — Parses logs into structured Python dicts
│   └── load.py            # L — Inserts structured data into PostgreSQL
├── db/
│   └── schema.sql         # PostgreSQL schema definitions
├── config.py              # Database credentials (gitignored)
├── main.py                # Orchestrates the full ETL pipeline
└── .gitignore
```

---

## Database Setup

- **Database engine:** PostgreSQL (installed system-wide via `apt`)
- **Database name:** `pokemon_db`
- **User:** `pokeuser` (full privileges granted)
- **Connection method:** TCP (`-h 127.0.0.1`) to bypass Unix socket peer authentication

---

## Database Schema

The schema is designed around the concept of the **team as the primary competitive unit**. Rather than treating individual Pokémon as isolated records, every Pokémon is anchored to a full 6-member team, which is itself anchored to a specific battle. This structure supports the core analytical goals of Phase 2 and beyond — computing team-level win rates, identifying common team compositions, and modeling metagame trends.

### Table: `battles`

The top-level record representing a single competitive match.

```sql
CREATE TABLE battles (
    battle_id   SERIAL PRIMARY KEY,
    showdown_id VARCHAR(100) UNIQUE,
    format      VARCHAR(50),
    date        TIMESTAMP,
    winner      VARCHAR(10),
    loser       VARCHAR(100),
    log_text    TEXT
);
```

| Column | Type | Description |
| :--- | :--- | :--- |
| `battle_id` | `SERIAL` (auto-increment integer) | Internal primary key |
| `showdown_id` | `VARCHAR(100)` UNIQUE | The Showdown replay ID (e.g. `gen9ou-2615146869`). Used for deduplication — re-running the pipeline skips already-loaded battles |
| `format` | `VARCHAR(50)` | Competitive format (e.g. `[Gen 9] OU`) |
| `date` | `TIMESTAMP` | Timestamp of the battle |
| `winner` | `VARCHAR(10)` | Which side won — stored as `p1` or `p2` rather than a player username, since player identity is irrelevant to team analysis |
| `loser` | `VARCHAR(100)` | Legacy column, unused in current pipeline |
| `log_text` | `TEXT` | Raw log content (reserved for future full-text analysis) |

---

### Table: `teams`

Represents one of the two competing teams in a battle. Every battle produces exactly two team records.

```sql
CREATE TABLE teams (
    team_id   SERIAL PRIMARY KEY,
    battle_id INTEGER REFERENCES battles(battle_id),
    player    VARCHAR(100),
    result    VARCHAR(10),
    team_hash VARCHAR(255)
);
```

| Column | Type | Description |
| :--- | :--- | :--- |
| `team_id` | `SERIAL` (auto-increment integer) | Internal primary key |
| `battle_id` | `INTEGER` (FK → `battles.battle_id`) | Links this team to its battle |
| `player` | `VARCHAR(100)` | Which side this team belongs to (`p1` or `p2`) |
| `result` | `VARCHAR(10)` | Outcome for this team — `win` or `loss` |
| `team_hash` | `VARCHAR(255)` | MD5 hash of the sorted, canonical 6-Pokémon names. Enables cross-battle team composition matching and deduplication in `team_compositions` |

---

### Table: `pokemon`

Represents a single Pokémon on a team. Every team record has exactly 6 associated Pokémon records.

```sql
CREATE TABLE pokemon (
    pokemon_id SERIAL PRIMARY KEY,
    team_id    INTEGER REFERENCES teams(team_id),
    name       VARCHAR(100),
    level      INTEGER,
    ability    VARCHAR(100),
    item       VARCHAR(100),
    tera_type  VARCHAR(50)
);
```

| Column | Type | Description |
| :--- | :--- | :--- |
| `pokemon_id` | `SERIAL` (auto-increment integer) | Internal primary key |
| `team_id` | `INTEGER` (FK → `teams.team_id`) | Links this Pokémon to its full team |
| `name` | `VARCHAR(100)` | Pokémon species name (e.g. `Great Tusk`, `Gholdengo`) |
| `level` | `INTEGER` | Level — typically 100 in competitive play |
| `ability` | `VARCHAR(100)` | Ability — populated when revealed during battle |
| `item` | `VARCHAR(100)` | Held item — populated when revealed during battle |
| `tera_type` | `VARCHAR(50)` | Tera type used if this Pokémon terastallized during the battle (e.g. `Fairy`, `Water`). `NULL` if the Pokémon did not terastallize |

---

### Table: `moves`

Represents observed moves for a Pokémon during a specific battle. Populated only from moves actually used — not from a predefined moveset — since Showdown logs only reveal moves as they are executed.

```sql
CREATE TABLE moves (
    move_id    SERIAL PRIMARY KEY,
    pokemon_id INTEGER REFERENCES pokemon(pokemon_id),
    name       VARCHAR(100),
    move_slot  INTEGER
);
```

| Column | Type | Description |
| :--- | :--- | :--- |
| `move_id` | `SERIAL` (auto-increment integer) | Internal primary key |
| `pokemon_id` | `INTEGER` (FK → `pokemon.pokemon_id`) | Links this move to its Pokémon |
| `name` | `VARCHAR(100)` | Move name (e.g. `Headlong Rush`, `Stealth Rock`) |
| `move_slot` | `INTEGER` | Slot order based on first appearance in the battle (1–4). Reflects usage order, not necessarily the in-game moveset slot order |

---

### Table: `battle_actions`

A sequential log of every meaningful event that occurred during a battle, stored in turn order.

```sql
CREATE TABLE battle_actions (
    action_id   SERIAL PRIMARY KEY,
    battle_id   INTEGER REFERENCES battles(battle_id),
    turn_order  INTEGER,
    action_type VARCHAR(50),
    actor       VARCHAR(100),
    move_used   VARCHAR(100),
    target      VARCHAR(100)
);
```

| Column | Type | Description |
| :--- | :--- | :--- |
| `action_id` | `SERIAL` (auto-increment integer) | Internal primary key |
| `battle_id` | `INTEGER` (FK → `battles.battle_id`) | Links this action to its battle |
| `turn_order` | `INTEGER` | Turn number this action occurred on |
| `action_type` | `VARCHAR(50)` | Type of event: `move`, `switch`, `damage`, or `terastallize` |
| `actor` | `VARCHAR(100)` | Which side performed the action (`p1` or `p2`) |
| `move_used` | `VARCHAR(100)` | Move name if `action_type` is `move`, otherwise `NULL` |
| `target` | `VARCHAR(100)` | Target side if applicable (`p1` or `p2`) |

---

### Table: `team_compositions`

An aggregate table that tracks how many times a specific 6-Pokémon team composition has been observed across all ingested battles, and how often it wins. This table is the foundation for metagame composition analysis in Phase 2.

```sql
CREATE TABLE team_compositions (
    comp_id    SERIAL PRIMARY KEY,
    team_hash  VARCHAR(255) UNIQUE,
    format     VARCHAR(50),
    first_seen TIMESTAMP,
    times_seen INTEGER DEFAULT 1,
    win_count  INTEGER DEFAULT 0
);
```

| Column | Type | Description |
| :--- | :--- | :--- |
| `comp_id` | `SERIAL` (auto-increment integer) | Internal primary key |
| `team_hash` | `VARCHAR(255)` UNIQUE | MD5 hash matching `teams.team_hash` — the unique identifier for this composition |
| `format` | `VARCHAR(50)` | Competitive format this composition was observed in |
| `first_seen` | `TIMESTAMP` | Timestamp of the first battle this composition appeared in |
| `times_seen` | `INTEGER` | Total number of times this exact composition has been observed. Incremented on every new battle via `ON CONFLICT ... DO UPDATE` |
| `win_count` | `INTEGER` | Number of times this composition has won. Reserved for future update logic |

---

## ETL Pipeline

### extract.py — Data Acquisition

Hits the Pokémon Showdown replay search API at `https://replay.pokemonshowdown.com/search.json` to collect replay IDs for a given format (default `gen9ou`). Downloads each replay's raw `.log` file into `raw_logs/`. Skips files already present on disk. Includes polite rate limiting via `time.sleep()` between requests to avoid hammering the API.

**Key behaviors:**
- Paginates through the search API to collect large volumes of replays
- Saves each log as `{showdown_id}.log` in `raw_logs/`
- Idempotent — re-running will not re-download existing files

---

### transform.py — Log Parsing

Parses the raw pipe-delimited Showdown log format line by line. Showdown logs use a `|tag|data|data|...` format where each line begins with a pipe character. The parser processes each line by splitting on `|` and dispatching on the tag.

**Key design decisions:**
- **Active Pokémon state tracking:** A dictionary `active_pokemon = {"p1": None, "p2": None}` is maintained throughout parsing. It is updated on every `|switch|` event and referenced on every `|move|` event, allowing moves to be attributed to the correct Pokémon without relying on the log's inline actor field alone.
- **Player name resolution:** The `|player|` tag maps `p1`/`p2` to usernames. Empty `|player|` lines (which appear at the end of some logs and would otherwise overwrite valid names) are ignored. Player names are used solely to resolve which pid won the battle, then discarded — they are not stored in the database.
- **Winner resolution:** The `|win|` tag provides the winning player's username. This is cross-referenced against the `players` dict to determine `winner_pid` (`p1` or `p2`), which is what gets stored in `battles.winner`.
- **Team hash generation:** After parsing, the full 6-Pokémon team list for each side is sorted alphabetically, joined into a canonical string, and MD5-hashed. This hash is deterministic regardless of team order in the log, enabling cross-battle composition matching.
- **Partial movesets:** Moves are only recorded when used in battle. Pokémon that are never sent out will have no move records. This is expected and acceptable — partial move data is still analytically useful for Phase 2 move frequency analysis.

**Parsed log tags:**

| Tag | Data Extracted |
| :--- | :--- |
| `\|tier\|` | Format name |
| `\|player\|` | pid-to-username mapping (temporary, for winner resolution only) |
| `\|poke\|` | Team composition — 6 Pokémon names per side from team preview |
| `\|turn\|` | Current turn number |
| `\|switch\|` | Switch event — updates active Pokémon state |
| `\|move\|` | Move used — attributed to active Pokémon, added to moveset |
| `\|-damage\|` | HP remaining after damage |
| `\|-terastallize\|` | Tera type — stored on the active Pokémon's moveset entry |
| `\|win\|` | Winning player username |

**Output structure per battle:**

```python
{
    "battle_id": "gen9ou-2615146869",
    "format": "[Gen 9] OU",
    "winner_pid": "p2",
    "teams": {
        "p1": ["Glimmora", "Great Tusk", "Gholdengo", "Dragapult", "Primarina", "Kingambit"],
        "p2": ["Volcanion", "Pelipper", "Iron Treads", "Kingdra", "Poliwrath", "Iron Valiant"]
    },
    "movesets": {
        "p1": {
            "Great Tusk": {"moves": ["Headlong Rush", "Rapid Spin", "Knock Off"], "tera_type": null},
            "Gholdengo":  {"moves": ["Nasty Plot", "Recover"], "tera_type": "Fairy"}
        },
        "p2": {
            "Kingdra":    {"moves": ["Weather Ball"], "tera_type": "Water"}
        }
    },
    "actions": [...],
    "team_hashes": {
        "p1": "b9e916a7219e5bce459b14e0c4c9d23c",
        "p2": "ab3859d75059174fcebbb2c501aec15a"
    }
}
```

---

### load.py — Database Insertion

Takes the parsed battle dictionaries and inserts them into PostgreSQL respecting the relational schema. Written to be fully idempotent and fault-tolerant.

**Key behaviors:**

- **Deduplication:** Before inserting any battle, checks `battles.showdown_id`. If the record already exists, the battle is skipped entirely.
- **Transaction isolation:** Each battle is wrapped in its own transaction. If any part of a battle's insertion fails, only that battle is rolled back — the rest of the run continues cleanly.
- **Insertion order:** Respects foreign key constraints by inserting in dependency order: `battles` → `teams` → `pokemon` → `moves`. `battle_actions` and `team_compositions` are inserted last.
- **Team composition upsert:** Uses PostgreSQL's `ON CONFLICT (team_hash) DO UPDATE` to either create a new composition record or increment `times_seen` on an existing one. This means composition statistics accumulate automatically across pipeline runs without manual aggregation.

**Insertion flow per battle:**

```
load_battle()         → INSERT INTO battles           → returns battle_id
load_teams()
  └── for each pid
        → INSERT INTO teams                           → returns team_id
        └── for each pokemon
              → INSERT INTO pokemon                   → returns pokemon_id
              └── for each move
                    → INSERT INTO moves
        → UPSERT INTO team_compositions
load_actions()        → INSERT INTO battle_actions (bulk)
conn.commit()
```

---

### main.py — Pipeline Orchestration

Runs the full ETL pipeline in sequence with a single command:

```bash
python3 main.py
```

Execution order: `extract` → `transform` → `load`

---

## Current Data

| Metric | Value |
| :--- | :--- |
| Format | Gen 9 OU |
| Battles ingested | 272 |
| Teams stored | 544 |
| Pokémon records | 3,264 |
| Move records | 5,177 |
| Unique team compositions | 394 |

The counts are internally consistent:
- 272 battles × 2 teams = **544 teams** ✓
- 544 teams × 6 Pokémon = **3,264 Pokémon** ✓
- ~1.6 observed moves per Pokémon on average — consistent with partial moveset visibility from replay data ✓
- 394 unique compositions out of 544 total teams confirms real composition overlap is being detected and tracked ✓

**Sample usage query result (validates data accuracy against known metagame trends):**

```
Great Tusk    — 9 appearances
Kingambit     — 7 appearances
Gholdengo     — 7 appearances
Hatterene     — 5 appearances
Glimmora      — 5 appearances
```

These results align with known Gen 9 OU usage statistics, confirming the pipeline is collecting and parsing data accurately.

---

## Foreign Key Relationship Map

```
battles
  └── teams           (battles.battle_id → teams.battle_id)
        └── pokemon   (teams.team_id → pokemon.team_id)
              └── moves (pokemon.pokemon_id → moves.pokemon_id)
  └── battle_actions  (battles.battle_id → battle_actions.battle_id)

team_compositions     (team_hash links to teams.team_hash — logical, not FK)
```

---

## Phase 1 Deliverable

A fully operational, idempotent ETL pipeline that:

- Downloads competitive replay data from Pokémon Showdown at scale
- Parses the raw pipe-delimited log format into structured relational data
- Correctly attributes moves, tera types, and team compositions to the right Pokémon and teams
- Stores all data in a normalized PostgreSQL schema designed around the team as the primary analytical unit
- Deduplicates at both the battle level and team composition level
- Produces a clean, queryable database ready for Phase 2 metagame analysis
