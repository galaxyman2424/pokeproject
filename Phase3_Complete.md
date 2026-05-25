# Phase 3 — Team Representation System: Complete

## Overview

Phase 3 builds a machine-readable feature representation layer on top of the Phase 1 database and Phase 2 analysis. Two new modules were written — a Pokémon data lookup layer and a feature engineering pipeline — producing a labeled numeric vector for every team in the dataset. Vectors were validated against known archetypes before the phase was closed.

---

## Environment

| Property | Value |
| :--- | :--- |
| Operating System | Linux Mint |
| IDE | VSCode |
| Project Location | `~/pokeproject` |
| Python Version | Python 3.12 |
| Virtual Environment | `~/pokeproject/venv` |
| Dataset | Gen 9 OU — 423 battles, 846 teams |

**No new Python dependencies were required for Phase 3.**
**Node.js v18** was used once to generate static JSON data files and is not required again.

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
│   ├── pokemon_data.py       # NEW — type/stat lookup layer
│   └── team_features.py      # NEW — feature engineering pipeline
├── data/
│   ├── dump_data.js          # Node.js script used once to generate JSON files
│   ├── pokedex.json          # Species types, base stats, abilities
│   └── typechart.json        # Type effectiveness encodings
├── output/
│   ├── pokemon_usage.csv / .json
│   ├── move_usage.csv / .json
│   ├── item_usage.csv / .json
│   ├── tera_rate.csv / .json
│   ├── tera_type_distribution.csv / .json
│   ├── pair_cooccurrence.csv / .json
│   ├── triplet_cooccurrence.csv / .json
│   ├── team_features.csv     # NEW — 846 labeled team vectors
│   ├── team_features.json    # NEW
│   └── meta.json
├── db/
│   └── schema.sql
├── config.py
├── main.py
└── .gitignore
```

---

## Data Sources

Pokémon type, base stat, and ability data was sourced from the `@pkmn/dex` npm package, which exposes the same data Pokémon Showdown uses internally. A one-time Node.js script (`data/dump_data.js`) was used to extract and serialize this data to `pokedex.json` and `typechart.json`. These files are static and do not need to be regenerated unless the game data changes.

The typechart uses Showdown's `damageTaken` encoding:

| Value | Meaning |
| :--- | :--- |
| `0` | 1x (neutral) |
| `1` | 2x (weak) |
| `2` | 0.5x (resist) |
| `3` | 0x (immune) |

Three Pokémon in the dataset had Showdown forme suffixes (`-*`) not present in the pokedex keys. These were resolved via a normalization map in `pokemon_data.py`:

| DB Name | Resolved To |
| :--- | :--- |
| `Dudunsparce-*` | `Dudunsparce` |
| `Greninja-*` | `Greninja` |
| `Zamazenta-*` | `Zamazenta` |

---

## Modules

### pokemon_data.py

Loads `pokedex.json` and `typechart.json` once at import time and exposes clean lookup functions used by the feature engineering pipeline.

**Key functions:**

| Function | Returns |
| :--- | :--- |
| `get_species(name)` | Full species dict or `None` |
| `get_types(name)` | List of type strings |
| `get_base_stat(name, stat)` | Integer base stat value |
| `get_weaknesses(name)` | Dict of `{type: multiplier}` for all 18 types |
| `get_abilities(name)` | List of ability strings |
| `normalize_name(name)` | Resolves forme suffixes to canonical names |

---

### team_features.py

Queries the database for all teams and their observed moves, computes a feature vector per team, and exports results to `output/`.

**Feature categories:**

**Defensive profile** (`def_*`) — for each of the 18 types, sums the effectiveness multipliers across all 6 Pokémon on the team. Higher values indicate greater exposure to that type.

**Offensive coverage** (`stab_*`) — for each of the 18 types, flags whether any Pokémon on the team has STAB of that type. Binary (0/1).

**Speed features** — `avg_base_speed`, `max_base_speed`, `min_base_speed` computed from base stat data.

**Role flags** — a mix of species-inferred and move-observed signals:

| Feature | Method | Description |
| :--- | :--- | :--- |
| `has_weather_setter` | Inferred | Species is a known weather setter |
| `has_rocks_setter` | Inferred | Species is a known Stealth Rock setter |
| `has_hazard_remover` | Inferred | Species is a known Rapid Spin / Defog user |
| `setup_observed` | Observed | A setup move (SD/NP/DD/CM) was used in this battle |
| `priority_observed` | Observed | A priority move was used in this battle |
| `pivot_observed` | Observed | A pivot move (U-turn/Volt Switch/Flip Turn) was used |
| `trick_room_observed` | Observed | Trick Room was used in this battle |

Each vector also carries a `result` column (`win`/`loss`) as the target label for Phase 7 machine learning.

---

## Output

| File | Description |
| :--- | :--- |
| `output/team_features.csv` | 846 rows × 47 feature columns + result label |
| `output/team_features.json` | Same data in records-oriented JSON |

**Total feature dimensions per team: 47**
- 18 defensive exposure floats
- 18 offensive STAB coverage booleans
- 3 speed floats
- 7 role flags
- 1 result label

---

## Validation

Feature vectors were cross-referenced against known archetypes pulled directly from the database.

**Rain teams** (Pelipper / Politoed present):

| team_id | result | has_weather_setter | has_hazard_remover |
| :--- | :--- | :--- | :--- |
| 632 | win | 1 | 1 |
| 764 | loss | 1 | 1 |
| 846 | loss | 1 | 0 |
| 940 | loss | 1 | 0 |
| 1366 | loss | 1 | 1 |

All 5 rain teams correctly flagged `has_weather_setter: 1`. ✓

**HO teams** (Deoxys-Speed present):

| team_id | result | has_rocks_setter | setup_observed | priority_observed |
| :--- | :--- | :--- | :--- | :--- |
| 815 | loss | 1 | 1 | 0 |
| 839 | loss | 1 | 1 | 0 |
| 888 | win | 1 | 1 | 1 |
| 1067 | loss | 1 | 1 | 1 |
| 1307 | loss | 1 | 1 | 0 |

All 5 HO teams correctly flagged `has_rocks_setter: 1` and `setup_observed: 1`. Teams with Dragonite correctly show `priority_observed: 1` (Extreme Speed). ✓

No anomalies detected.

---

## Win Rate Correlation (Defensive Exposure)

A quick Pearson correlation between defensive exposure features and win rate surfaced the following signal:

**Negatively correlated with winning** (being weak to these types hurts):
- Normal, Steel, Grass, Poison, Psychic

**Positively correlated with winning** (teams that take more Ghost damage tend to win more):
- Ghost, Fire, Ground, Dark, Ice

The Ghost correlation is consistent with Gen 9 OU — Dragapult and Gholdengo are among the strongest Pokémon in the format, and teams built around them tend to win more. Correlations are weak at this dataset size and will strengthen as more replays are ingested.

---

## Phase 3 Deliverable

A complete team representation layer that:

- Loads Pokémon type, stat, and ability data from static JSON files derived from Showdown's own data
- Computes 47-dimensional numeric feature vectors for all 846 teams in the dataset
- Combines species-inferred role signals with battle-observed move signals
- Validates output against known archetypes with no anomalies detected
- Exports labeled vectors to CSV and JSON ready for Phase 4 threat analysis and Phase 7 machine learning
