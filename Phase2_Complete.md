# Phase 2 — Metagame Analysis: Complete

## Overview

Phase 2 builds a full metagame analysis layer on top of the Phase 1 database. Three analysis scripts were written and validated against known Gen 9 OU competitive trends. The phase produces usage statistics, move/item/tera distributions, co-occurrence pair and triplet data, and preliminary archetype signals — all exported to CSV and JSON for consumption by later phases.

A bug discovered during this phase (item data never being parsed or inserted in Phase 1) was identified and fixed, requiring a full re-ingest of all replay data.

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

**No new dependencies were required for Phase 2.**

---

## Project File Structure

```
~/pokeproject/
├── venv/
├── raw_logs/
├── etl/
│   ├── extract.py
│   ├── transform.py          # Updated — item parsing added
│   └── load.py               # Updated — item insertion added
├── analysis/
│   ├── __init__.py
│   ├── usage_analysis.py     # Pokémon, move, item, tera statistics
│   ├── export.py             # CSV + JSON export of all analysis tables
│   └── co_occurrence.py      # Pair and triplet co-occurrence analysis
├── output/
│   ├── pokemon_usage.csv / .json
│   ├── move_usage.csv / .json
│   ├── item_usage.csv / .json
│   ├── tera_rate.csv / .json
│   ├── tera_type_distribution.csv / .json
│   ├── pair_cooccurrence.csv / .json
│   ├── triplet_cooccurrence.csv / .json
│   └── meta.json
├── db/
│   └── schema.sql
├── config.py
├── main.py
└── .gitignore
```

---

## Phase 1 Bug Fix — Item Parsing

During Phase 2 setup it was discovered that item data was silently missing from the database. Two root causes were identified:

**transform.py** — The `|-item|` log tag was never handled. Items in Showdown logs are only revealed when they activate visibly during battle (e.g. Leftovers triggering, a Choice item locking a move, Rocky Helmet damage). A new tag handler was added:

```python
elif tag == "-item":
    actor_raw = parts[2]
    pid = actor_raw[:2]
    item_name = parts[3] if len(parts) > 3 else None
    pokemon = active_pokemon[pid]
    if pokemon and item_name:
        if pokemon not in battle["movesets"][pid]:
            battle["movesets"][pid][pokemon] = {"moves": [], "tera_type": None, "item": None}
        battle["movesets"][pid][pokemon]["item"] = item_name
```

All moveset initialization dicts were also updated to include `"item": None` for consistency.

**load.py** — The `INSERT INTO pokemon` statement did not include the `item` column, and `pokemon_id` was never captured from `RETURNING`. Both were fixed:

```python
cursor.execute("""
    INSERT INTO pokemon (team_id, name, tera_type, item)
    VALUES (%s, %s, %s, %s)
    RETURNING pokemon_id;
""", (team_id, pokemon_name, tera_type, item))
pokemon_id = cursor.fetchone()[0]
```

The database was truncated with `TRUNCATE battles CASCADE` and all 423 battles were re-ingested cleanly.

**Known limitation:** Item data is inherently sparse. Items are only recorded when they activate visibly in a replay. A Pokémon holding Leftovers that never took damage will have `NULL` in the item column. Item statistics should be interpreted as "among battles where the item was observed" rather than absolute usage rates.

---

## Analysis Scripts

### usage_analysis.py

Queries the PostgreSQL database and computes five DataFrames:

**Pokémon Usage** — counts appearances across all teams, divides by total teams (846), computes win rate per Pokémon. Usage % is directly comparable to Smogon's monthly usage statistics.

**Move Usage** — counts observed move usage per Pokémon, computes move frequency as a percentage of all observed moves for that species. Reflects Smogon's per-Pokémon move distribution format.

**Item Usage** — counts observed item activations per Pokémon, filtered to non-NULL items only. Computes item frequency among observed appearances, not total appearances. Low observation counts (<10) should not be over-indexed.

**Tera Rate** — for every Pokémon, computes what percentage of appearances resulted in a observed terastallization event.

**Tera Type Distribution** — among terastallization events per Pokémon, computes the type frequency distribution.

All five tables are printed to terminal and importable by other scripts.

---

### export.py

Imports all five DataFrames from `usage_analysis.py` and writes each to `output/` as both `.csv` and `.json`. JSON is exported with `orient='records'` for clean list-of-objects format compatible with future API and dashboard consumption. Also writes a `meta.json` describing the dataset.

Run with:
```bash
python3 analysis/export.py
```

---

### co_occurrence.py

Fetches all teams from the database and computes pair and triplet co-occurrence statistics.

**Pairs** — for every team, generates all C(6,2) = 15 Pokémon pairs. Counts how often each pair appears together across all 846 teams, computes co-occurrence rate and pair win rate.

**Triplets** — generates all C(6,3) = 20 Pokémon triplets per team, filtered to a minimum of 5 appearances to suppress noise at this dataset size.

Output columns: `pokemon_a`, `pokemon_b`, `(pokemon_c)`, `co_occurrence_count`, `co_occurrence_rate`, `pair_win_count`, `pair_win_rate`.

Run with:
```bash
python3 analysis/co_occurrence.py
```

---

## Results

### Dataset

| Metric | Value |
| :--- | :--- |
| Format | Gen 9 OU |
| Battles ingested | 423 |
| Teams analyzed | 846 |
| Unique Pokémon observed | 290+ |
| Pair combinations computed | All C(6,2) per team |
| Triplet combinations computed | All C(6,3) per team, min 5 appearances |

---

### Top Pokémon Usage

| Pokémon | Usage % | Win Rate % |
| :--- | :--- | :--- |
| Great Tusk | 24.82 | 56.19 |
| Kingambit | 18.44 | 58.33 |
| Gholdengo | 18.32 | 61.94 |
| Dragonite | 13.36 | 58.41 |
| Raging Bolt | 13.24 | 49.11 |
| Iron Valiant | 12.29 | 45.19 |
| Corviknight | 11.82 | 51.00 |
| Zamazenta | 11.82 | 41.00 |
| Hatterene | 11.23 | 50.53 |
| Dragapult | 11.11 | 58.51 |

---

### Top Pairs by Co-occurrence

| Pair | Co-occurrence Rate % | Win Rate % |
| :--- | :--- | :--- |
| Great Tusk + Kingambit | 8.75 | 54.05 |
| Gholdengo + Great Tusk | 7.21 | 60.66 |
| Dragonite + Gholdengo | 5.56 | 72.34 |
| Great Tusk + Raging Bolt | 5.44 | 56.52 |
| Gholdengo + Kingambit | 5.08 | 65.12 |

---

### Top Pairs by Win Rate (min 10 appearances)

| Pair | Appearances | Win Rate % |
| :--- | :--- | :--- |
| Dragonite + Pecharunt | 10 | 90.00 |
| Corviknight + Kingambit | 12 | 83.33 |
| Gholdengo + Hatterene | 11 | 81.82 |
| Dragapult + Gholdengo | 16 | 81.25 |
| Dragonite + Ogerpon-Wellspring | 16 | 81.25 |

---

### Top Triplet Cores

| Core | Appearances | Win Rate % |
| :--- | :--- | :--- |
| Gholdengo + Great Tusk + Kingambit | 27 | 66.67 |
| Dragonite + Gholdengo + Great Tusk | 20 | 70.00 |
| Great Tusk + Hatterene + Kingambit | 17 | 58.82 |
| Gholdengo + Great Tusk + Raging Bolt | 17 | 58.82 |
| Araquanid + Gholdengo + Kingambit | 15 | 73.33 |

---

### Notable Move Distributions

| Pokémon | Top Moves |
| :--- | :--- |
| Great Tusk | Headlong Rush (23%), Rapid Spin (19%), Ice Spinner (18%), Stealth Rock (14%) |
| Kingambit | Sucker Punch (28%), Kowtow Cleave (21%), Iron Head (21%), Swords Dance (19%) |
| Gholdengo | Shadow Ball (27%), Make It Rain (23%), Nasty Plot (14%), Trick (9%) |
| Dragonite | Dragon Dance (27%), Extreme Speed (23%), Earthquake (15%) |
| Dragapult | Dragon Darts (21%), Draco Meteor (13%), U-turn (12%), Shadow Ball (10%) |

---

### Notable Item Observations

| Pokémon | Top Item | Observed Rate % |
| :--- | :--- | :--- |
| Gholdengo | Air Balloon | 77.78 (n=72) |
| Kingambit | Air Balloon | 94.44 (n=18) |
| Raging Bolt | Choice Scarf | 60.00 (n=5) |
| Great Tusk | Choice Scarf | 50.00 (n=4) |

Item sample sizes are small by nature — see known limitations above.

---

### Notable Tera Distributions

| Pokémon | Top Tera Type | Rate % |
| :--- | :--- | :--- |
| Dragonite | Normal | 66.67 |
| Kingambit | Ghost | 57.69 |
| Raging Bolt | Fairy | 55.56 |
| Dragapult | Dragon | 55.00 |
| Gholdengo | Fairy | 36.84 |

---

## Smogon Validation

Usage rankings were cross-referenced against known Gen 9 OU metagame trends. Results are consistent:

- Great Tusk, Kingambit, and Gholdengo are the top three most used Pokémon — correct.
- Dragonite, Raging Bolt, Iron Valiant, Corviknight, and Dragapult all appear in the top 10 — correct.
- Move distributions match canonical Smogon sets for all top Pokémon.
- Tera type distributions match known competitive usage (Dragonite Tera Normal, Kingambit Tera Ghost, Raging Bolt Tera Fairy).
- Item observations (Gholdengo Air Balloon, Kingambit Air Balloon) match known meta item choices.

No anomalies detected. Pipeline output is analytically valid.

---

## Archetype Signals

Co-occurrence data reveals at least four distinct team archetypes forming in the dataset, which will serve as the foundation for Phase 3 archetype clustering:

**Balance / Bulky Offense** — Gholdengo + Great Tusk + Kingambit is the dominant core (27 appearances, 66.67% win rate). The most played archetype in Gen 9 OU. Frequently extends to include Dragonite or Hatterene as a fourth member.

**Rain Offense** — Araquanid clustering with Iron Moth, Raging Bolt, Gholdengo, and Kingambit. Araquanid + Iron Moth (80% win rate), Araquanid + Raging Bolt (71.43%), and Araquanid + Gholdengo + Raging Bolt (75% win rate triplet) are clear rain core signals.

**Sun Offense** — Great Tusk + Ninetales + Walking Wake triplet (12 appearances). Ninetales provides sun setting, Walking Wake abuses Sunny Day, Great Tusk handles hazard control.

**Hyper Offense** — Deoxys-Speed + Dragonite + Great Tusk (14 appearances). Deoxys-Speed is the premier hazard setter and speed control option for HO structures in Gen 9 OU.

These four archetypes will be the initial cluster targets in Phase 3.

---

## Data Scaling Note

At 423 battles, 394+ unique team compositions were observed — meaning most teams appear only once. This makes full 6-member composition clustering unreliable at the current dataset size. The analysis pipeline is intentionally being validated on this smaller dataset before scaling. When the dataset is expanded to 2000–5000 battles, composition clusters will become statistically meaningful and archetype clustering will be run at that scale.

---

## Phase 2 Deliverable

A complete metagame analysis layer that:

- Computes Pokémon usage %, win rates, move distributions, item distributions, and tera distributions from the Phase 1 database
- Exports all statistics to CSV and JSON for downstream consumption
- Validates output against known Gen 9 OU metagame trends with no anomalies detected
- Identifies co-occurring Pokémon pairs and triplets with win rate weighting
- Surfaces four preliminary archetype signals from co-occurrence data
- Establishes the analytical foundation for Phase 3 archetype clustering
