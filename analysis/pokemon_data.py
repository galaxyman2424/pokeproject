import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

# damageTaken encoding from Showdown
# 0 = normal (1x), 1 = 2x weak, 2 = 4x weak, 3 = immune
DAMAGE_TAKEN_MAP = {0: 1.0, 1: 2.0, 2: 0.5, 3: 0.0}

ALL_TYPES = [
    "Bug", "Dark", "Dragon", "Electric", "Fairy", "Fighting",
    "Fire", "Flying", "Ghost", "Grass", "Ground", "Ice",
    "Normal", "Poison", "Psychic", "Rock", "Steel", "Water"
]

def load_pokedex() -> dict:
    with open(DATA_DIR / "pokedex.json") as f:
        return json.load(f)

def load_typechart() -> dict:
    with open(DATA_DIR / "typechart.json") as f:
        return json.load(f)

# Load once at module level so every import shares the same dict
_POKEDEX = load_pokedex()
_TYPECHART = load_typechart()

def get_species(name: str) -> dict | None:
    name = normalize_name(name)
    return _POKEDEX.get(name)


def get_base_stat(name: str, stat: str) -> int | None:
    """Get a single base stat for a species. stat = hp/atk/def/spa/spd/spe."""
    species = get_species(name)
    if species is None:
        return None
    return species["baseStats"].get(stat)


def get_types(name: str) -> list[str]:
    """Get the types of a species as a list."""
    species = get_species(name)
    if species is None:
        return []
    return species["types"]


def get_type_effectiveness(attacking_type: str, defending_types: list[str]) -> float:
    """
    Compute the combined effectiveness multiplier of an attacking type
    against a Pokémon with the given defending types.
    """
    multiplier = 1.0
    for def_type in defending_types:
        type_data = _TYPECHART.get(def_type, {})
        damage_taken = type_data.get("damageTaken", {})
        encoding = damage_taken.get(attacking_type, 0)
        multiplier *= DAMAGE_TAKEN_MAP[encoding]
    return multiplier


def get_weaknesses(name: str) -> dict[str, float]:
    """
    Return a dict of {attacking_type: multiplier} for all 18 types
    against the given Pokémon. Values > 1.0 are weaknesses.
    """
    types = get_types(name)
    return {
        t: get_type_effectiveness(t, types)
        for t in ALL_TYPES
    }


def get_abilities(name: str) -> list[str]:
    species = get_species(name)
    if species is None:
        return []
    return species.get("abilities", [])

def normalize_name(name: str) -> str:
    """Normalize Showdown forme names to pokedex keys."""
    replacements = {
        "Dudunsparce-*": "Dudunsparce",
        "Greninja-*": "Greninja",
        "Zamazenta-*": "Zamazenta",
    }
    return replacements.get(name, name)