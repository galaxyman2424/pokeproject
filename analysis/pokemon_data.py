import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

ALL_TYPES = [
    "Bug", "Dark", "Dragon", "Electric", "Fairy", "Fighting",
    "Fire", "Flying", "Ghost", "Grass", "Ground", "Ice",
    "Normal", "Poison", "Psychic", "Rock", "Steel", "Water"
]

# TYPE_CHART[attacking][defending] = multiplier
# 0.0 = immune, 0.5 = resist, 1.0 = neutral, 2.0 = super effective
TYPE_CHART = {
    "Bug":      {"Bug":1.0,"Dark":2.0,"Dragon":1.0,"Electric":1.0,"Fairy":0.5,"Fighting":0.5,"Fire":0.5,"Flying":0.5,"Ghost":0.5,"Grass":2.0,"Ground":1.0,"Ice":1.0,"Normal":1.0,"Poison":0.5,"Psychic":2.0,"Rock":1.0,"Steel":0.5,"Water":1.0},
    "Dark":     {"Bug":1.0,"Dark":0.5,"Dragon":1.0,"Electric":1.0,"Fairy":0.5,"Fighting":0.5,"Fire":1.0,"Flying":1.0,"Ghost":0.5,"Grass":1.0,"Ground":1.0,"Ice":1.0,"Normal":1.0,"Poison":1.0,"Psychic":2.0,"Rock":1.0,"Steel":0.5,"Water":1.0},
    "Dragon":   {"Bug":1.0,"Dark":1.0,"Dragon":2.0,"Electric":1.0,"Fairy":0.0,"Fighting":1.0,"Fire":1.0,"Flying":1.0,"Ghost":1.0,"Grass":1.0,"Ground":1.0,"Ice":1.0,"Normal":1.0,"Poison":1.0,"Psychic":1.0,"Rock":1.0,"Steel":0.5,"Water":1.0},
    "Electric": {"Bug":1.0,"Dark":1.0,"Dragon":0.5,"Electric":0.5,"Fairy":1.0,"Fighting":1.0,"Fire":1.0,"Flying":2.0,"Ghost":1.0,"Grass":0.5,"Ground":0.0,"Ice":1.0,"Normal":1.0,"Poison":1.0,"Psychic":1.0,"Rock":1.0,"Steel":1.0,"Water":2.0},
    "Fairy":    {"Bug":1.0,"Dark":2.0,"Dragon":2.0,"Electric":1.0,"Fairy":1.0,"Fighting":2.0,"Fire":0.5,"Flying":1.0,"Ghost":1.0,"Grass":1.0,"Ground":1.0,"Ice":1.0,"Normal":1.0,"Poison":0.5,"Psychic":1.0,"Rock":1.0,"Steel":0.5,"Water":1.0},
    "Fighting": {"Bug":0.5,"Dark":2.0,"Dragon":1.0,"Electric":1.0,"Fairy":0.5,"Fighting":1.0,"Fire":1.0,"Flying":0.5,"Ghost":0.0,"Grass":1.0,"Ground":1.0,"Ice":2.0,"Normal":2.0,"Poison":0.5,"Psychic":0.5,"Rock":2.0,"Steel":2.0,"Water":1.0},
    "Fire":     {"Bug":2.0,"Dark":1.0,"Dragon":0.5,"Electric":1.0,"Fairy":1.0,"Fighting":1.0,"Fire":0.5,"Flying":1.0,"Ghost":1.0,"Grass":2.0,"Ground":1.0,"Ice":2.0,"Normal":1.0,"Poison":1.0,"Psychic":1.0,"Rock":0.5,"Steel":2.0,"Water":0.5},
    "Flying":   {"Bug":2.0,"Dark":1.0,"Dragon":1.0,"Electric":0.5,"Fairy":1.0,"Fighting":2.0,"Fire":1.0,"Flying":1.0,"Ghost":1.0,"Grass":2.0,"Ground":2.0,"Ice":1.0,"Normal":1.0,"Poison":1.0,"Psychic":1.0,"Rock":0.5,"Steel":0.5,"Water":1.0},
    "Ghost":    {"Bug":1.0,"Dark":0.5,"Dragon":1.0,"Electric":1.0,"Fairy":1.0,"Fighting":1.0,"Fire":1.0,"Flying":1.0,"Ghost":2.0,"Grass":1.0,"Ground":1.0,"Ice":1.0,"Normal":0.0,"Poison":1.0,"Psychic":2.0,"Rock":1.0,"Steel":1.0,"Water":1.0},
    "Grass":    {"Bug":0.5,"Dark":1.0,"Dragon":0.5,"Electric":1.0,"Fairy":1.0,"Fighting":1.0,"Fire":0.5,"Flying":0.5,"Ghost":1.0,"Grass":0.5,"Ground":2.0,"Ice":1.0,"Normal":1.0,"Poison":0.5,"Psychic":1.0,"Rock":2.0,"Steel":0.5,"Water":2.0},
    "Ground":   {"Bug":0.5,"Dark":1.0,"Dragon":1.0,"Electric":2.0,"Fairy":1.0,"Fighting":1.0,"Fire":2.0,"Flying":0.0,"Ghost":1.0,"Grass":0.5,"Ground":1.0,"Ice":1.0,"Normal":1.0,"Poison":2.0,"Psychic":1.0,"Rock":2.0,"Steel":2.0,"Water":1.0},
    "Ice":      {"Bug":1.0,"Dark":1.0,"Dragon":2.0,"Electric":1.0,"Fairy":1.0,"Fighting":1.0,"Fire":0.5,"Flying":2.0,"Ghost":1.0,"Grass":2.0,"Ground":2.0,"Ice":0.5,"Normal":1.0,"Poison":1.0,"Psychic":1.0,"Rock":1.0,"Steel":0.5,"Water":0.5},
    "Normal":   {"Bug":1.0,"Dark":1.0,"Dragon":1.0,"Electric":1.0,"Fairy":1.0,"Fighting":1.0,"Fire":1.0,"Flying":1.0,"Ghost":0.0,"Grass":1.0,"Ground":1.0,"Ice":1.0,"Normal":1.0,"Poison":1.0,"Psychic":1.0,"Rock":0.5,"Steel":0.5,"Water":1.0},
    "Poison":   {"Bug":1.0,"Dark":1.0,"Dragon":1.0,"Electric":1.0,"Fairy":2.0,"Fighting":1.0,"Fire":1.0,"Flying":1.0,"Ghost":0.5,"Grass":2.0,"Ground":0.5,"Ice":1.0,"Normal":1.0,"Poison":0.5,"Psychic":1.0,"Rock":0.5,"Steel":0.0,"Water":1.0},
    "Psychic":  {"Bug":1.0,"Dark":0.5,"Dragon":1.0,"Electric":1.0,"Fairy":1.0,"Fighting":2.0,"Fire":1.0,"Flying":1.0,"Ghost":1.0,"Grass":1.0,"Ground":1.0,"Ice":1.0,"Normal":1.0,"Poison":2.0,"Psychic":0.5,"Rock":1.0,"Steel":0.5,"Water":1.0},
    "Rock":     {"Bug":2.0,"Dark":1.0,"Dragon":1.0,"Electric":1.0,"Fairy":1.0,"Fighting":0.5,"Fire":2.0,"Flying":2.0,"Ghost":1.0,"Grass":1.0,"Ground":0.5,"Ice":2.0,"Normal":1.0,"Poison":1.0,"Psychic":1.0,"Rock":1.0,"Steel":0.5,"Water":1.0},
    "Steel":    {"Bug":1.0,"Dark":1.0,"Dragon":1.0,"Electric":0.5,"Fairy":2.0,"Fighting":1.0,"Fire":0.5,"Flying":1.0,"Ghost":1.0,"Grass":1.0,"Ground":1.0,"Ice":2.0,"Normal":1.0,"Poison":1.0,"Psychic":1.0,"Rock":2.0,"Steel":0.5,"Water":0.5},
    "Water":    {"Bug":1.0,"Dark":1.0,"Dragon":0.5,"Electric":1.0,"Fairy":1.0,"Fighting":1.0,"Fire":2.0,"Flying":1.0,"Ghost":1.0,"Grass":0.5,"Ground":2.0,"Ice":1.0,"Normal":1.0,"Poison":1.0,"Psychic":1.0,"Rock":2.0,"Steel":1.0,"Water":0.5},
}

def load_pokedex() -> dict:
    with open(DATA_DIR / "pokedex.json") as f:
        return json.load(f)

_POKEDEX = load_pokedex()

def get_species(name: str) -> dict | None:
    name = normalize_name(name)
    return _POKEDEX.get(name)

def get_base_stat(name: str, stat: str) -> int | None:
    species = get_species(name)
    if species is None:
        return None
    return species["baseStats"].get(stat)

def get_types(name: str) -> list[str]:
    species = get_species(name)
    if species is None:
        return []
    return species["types"]

def get_type_effectiveness(attacking_type: str, defending_types: list[str]) -> float:
    multiplier = 1.0
    for def_type in defending_types:
        multiplier *= TYPE_CHART.get(attacking_type, {}).get(def_type, 1.0)
    return multiplier

def get_weaknesses(name: str) -> dict[str, float]:
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
    replacements = {
        "Dudunsparce-*": "Dudunsparce",
        "Greninja-*": "Greninja",
        "Zamazenta-*": "Zamazenta",
    }
    return replacements.get(name, name)