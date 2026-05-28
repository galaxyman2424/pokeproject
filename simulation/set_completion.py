"""
simulation/set_completion.py

Fills in complete legal Pokémon sets for simulation.
Sources moves from the Phase 2 move_usage data, items from item_usage data,
and falls back to sensible defaults when data is sparse.

Usage:
    from simulation.set_completion import complete_team
    sets = complete_team(["Great Tusk", "Gholdengo", "Kingambit", ...])
"""

import sys
import pandas as pd
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from analysis.pokemon_data import get_types, get_base_stat, get_abilities

OUTPUT_DIR = Path(__file__).parent.parent / "output"

# ──────────────────────────────────────────────────────────────────────────────
# Default fallbacks
# ──────────────────────────────────────────────────────────────────────────────

# Nature defaults by role inference from speed/attack stats
DEFAULT_NATURE = "Hardy"

# EV spreads — physical attacker / special attacker / bulky defaults
PHYSICAL_NATURE  = "Adamant"
SPECIAL_NATURE   = "Modest"
SPEED_NATURE_PHY = "Jolly"
SPEED_NATURE_SPC = "Timid"

DEFAULT_EVS = {"hp": 0, "atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0}
OFFENSIVE_PHYSICAL_EVS = {"hp": 4,   "atk": 252, "def": 0, "spa": 0, "spd": 0, "spe": 252}
OFFENSIVE_SPECIAL_EVS  = {"hp": 4,   "atk": 0,   "def": 0, "spa": 252, "spd": 0, "spe": 252}
BULKY_PHYSICAL_EVS     = {"hp": 252, "atk": 4,   "def": 252, "spa": 0, "spd": 0, "spe": 0}
BULKY_SPECIAL_EVS      = {"hp": 252, "atk": 0,   "def": 0, "spa": 4, "spd": 252, "spe": 0}

# Item defaults per Pokémon when item_usage has no data
ITEM_DEFAULTS = {
    "Great Tusk":         "Heavy-Duty Boots",
    "Kingambit":          "Air Balloon",
    "Gholdengo":          "Air Balloon",
    "Dragonite":          "Heavy-Duty Boots",
    "Corviknight":        "Rocky Helmet",
    "Hatterene":          "Choice Scarf",
    "Raging Bolt":        "Choice Scarf",
    "Dragapult":          "Choice Specs",
    "Iron Valiant":       "Choice Scarf",
    "Zamazenta":          "Rusted Shield",
    "Pelipper":           "Damp Rock",
    "Politoed":           "Damp Rock",
    "Iron Treads":        "Heavy-Duty Boots",
    "Glimmora":           "Loaded Dice",
    "Ting-Lu":            "Leftovers",
    "Ogerpon-Wellspring": "Wellspring Mask",
    "Ninetales":          "Heat Rock",
    "Walking Wake":       "Choice Specs",
    "Araquanid":          "Mystic Water",
    "Deoxys-Speed":       "Focus Sash",
}

DEFAULT_ITEM = "Leftovers"

# Tera type defaults
TERA_DEFAULTS = {
    "Dragonite":  "Normal",
    "Kingambit":  "Ghost",
    "Raging Bolt":"Fairy",
    "Dragapult":  "Dragon",
    "Gholdengo":  "Fairy",
    "Great Tusk": "Ground",
    "Hatterene":  "Psychic",
}
DEFAULT_TERA = "Normal"

# Ability defaults (first ability from pokedex when not otherwise specified)
ABILITY_OVERRIDES = {
    "Great Tusk":   "Protosynthesis",
    "Gholdengo":    "Good as Gold",
    "Kingambit":    "Supreme Overlord",
    "Dragonite":    "Multiscale",
    "Corviknight":  "Pressure",
    "Hatterene":    "Magic Bounce",
    "Raging Bolt":  "Protosynthesis",
    "Dragapult":    "Clear Body",
    "Iron Valiant": "Quark Drive",
    "Pelipper":     "Drizzle",
    "Politoed":     "Drizzle",
    "Iron Treads":  "Quark Drive",
    "Glimmora":     "Toxic Debris",
    "Ting-Lu":      "Vessel of Ruin",
    "Ninetales":    "Drought",
}

# ──────────────────────────────────────────────────────────────────────────────
# Load Phase 2 data
# ──────────────────────────────────────────────────────────────────────────────

def _load_move_usage() -> pd.DataFrame:
    path = OUTPUT_DIR / "move_usage.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame(columns=["pokemon", "move", "times_used", "move_pct"])


def _load_item_usage() -> pd.DataFrame:
    path = OUTPUT_DIR / "item_usage.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame(columns=["pokemon", "item", "times_seen", "item_pct", "total_observed"])


_MOVE_USAGE = _load_move_usage()
_ITEM_USAGE = _load_item_usage()


# ──────────────────────────────────────────────────────────────────────────────
# Role inference
# ──────────────────────────────────────────────────────────────────────────────

def _infer_role(name: str) -> str:
    """
    Infer offensive role from base stats to pick EV spread and nature.
    Returns: 'physical_offense', 'special_offense', 'physical_bulk', 'special_bulk'
    """
    atk = get_base_stat(name, "atk") or 0
    spa = get_base_stat(name, "spa") or 0
    spe = get_base_stat(name, "spe") or 0
    hp  = get_base_stat(name, "hp")  or 0
    defn= get_base_stat(name, "def") or 0
    spd = get_base_stat(name, "spd") or 0

    # If fast and strong attacker → offensive spread
    if spe >= 80:
        if atk >= spa:
            return "physical_offense"
        else:
            return "special_offense"
    # Slow and bulky → defensive spread
    if atk >= spa:
        return "physical_bulk"
    return "special_bulk"


# ──────────────────────────────────────────────────────────────────────────────
# Move completion
# ──────────────────────────────────────────────────────────────────────────────

def _get_moves(name: str, known_moves: list[str]) -> list[str]:
    """
    Fill a 4-move slot from Phase 2 data. Known moves from replay data take
    priority. Remaining slots filled by most-used moves not already included.
    """
    moves = list(known_moves)  # copy

    if len(moves) >= 4:
        return moves[:4]

    # Pull top moves for this Pokémon from move_usage
    poke_moves = _MOVE_USAGE[_MOVE_USAGE["pokemon"] == name]
    if not poke_moves.empty:
        ranked = poke_moves.sort_values("times_used", ascending=False)["move"].tolist()
        for m in ranked:
            if m not in moves:
                moves.append(m)
            if len(moves) == 4:
                break

    # Still short — pad with Tackle as a harmless legal filler
    while len(moves) < 4:
        moves.append("Tackle")

    return moves[:4]


# ──────────────────────────────────────────────────────────────────────────────
# Item completion
# ──────────────────────────────────────────────────────────────────────────────

def _get_item(name: str, known_item: str | None) -> str:
    if known_item:
        return known_item

    # Try item_usage data (most commonly observed item)
    poke_items = _ITEM_USAGE[_ITEM_USAGE["pokemon"] == name]
    if not poke_items.empty:
        top = poke_items.sort_values("times_seen", ascending=False).iloc[0]
        if top["times_seen"] >= 3:   # only trust if observed at least 3 times
            return top["item"]

    return ITEM_DEFAULTS.get(name, DEFAULT_ITEM)


# ──────────────────────────────────────────────────────────────────────────────
# Ability completion
# ──────────────────────────────────────────────────────────────────────────────

def _get_ability(name: str) -> str:
    if name in ABILITY_OVERRIDES:
        return ABILITY_OVERRIDES[name]
    abilities = get_abilities(name)
    return abilities[0] if abilities else ""


# ──────────────────────────────────────────────────────────────────────────────
# EV / nature completion
# ──────────────────────────────────────────────────────────────────────────────

def _get_evs_and_nature(name: str) -> tuple[dict, str]:
    role = _infer_role(name)
    if role == "physical_offense":
        return OFFENSIVE_PHYSICAL_EVS, SPEED_NATURE_PHY
    elif role == "special_offense":
        return OFFENSIVE_SPECIAL_EVS, SPEED_NATURE_SPC
    elif role == "physical_bulk":
        return BULKY_PHYSICAL_EVS, PHYSICAL_NATURE
    else:
        return BULKY_SPECIAL_EVS, SPECIAL_NATURE


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def complete_set(
    name: str,
    known_moves: list[str] | None = None,
    known_item: str | None = None,
    known_tera: str | None = None,
) -> dict:
    """
    Build a complete legal set for a single Pokémon.

    Args:
        name:        Species name (e.g. "Great Tusk")
        known_moves: Moves observed in replay data (may be partial or empty)
        known_item:  Item observed in replay data (may be None)
        known_tera:  Tera type observed in replay data (may be None)

    Returns:
        A complete set dict ready for build_packed_team()
    """
    known_moves = known_moves or []
    evs, nature = _get_evs_and_nature(name)

    return {
        "name":      name,
        "species":   name,
        "item":      _get_item(name, known_item),
        "ability":   _get_ability(name),
        "moves":     _get_moves(name, known_moves),
        "nature":    nature,
        "evs":       evs,
        "ivs":       {"hp":31,"atk":31,"def":31,"spa":31,"spd":31,"spe":31},
        "level":     100,
        "tera_type": known_tera or TERA_DEFAULTS.get(name, DEFAULT_TERA),
    }


def complete_team(
    pokemon_names: list[str],
    movesets: dict | None = None,
) -> list[dict]:
    """
    Build complete sets for a full team.

    Args:
        pokemon_names: List of 6 species names
        movesets:      Optional dict of {name: {"moves": [...], "item": ..., "tera_type": ...}}
                       as produced by transform.py. Partial data is fine.

    Returns:
        List of 6 complete set dicts
    """
    movesets = movesets or {}
    sets = []
    for name in pokemon_names:
        ms = movesets.get(name, {})
        sets.append(complete_set(
            name=name,
            known_moves=ms.get("moves", []),
            known_item=ms.get("item"),
            known_tera=ms.get("tera_type"),
        ))
    return sets


if __name__ == "__main__":
    # Quick smoke test
    team = ["Great Tusk", "Gholdengo", "Kingambit", "Dragonite", "Hatterene", "Corviknight"]
    sets = complete_team(team)
    for s in sets:
        print(f"{s['name']:20} | {s['item']:25} | {s['ability']:20} | {', '.join(s['moves'])}")