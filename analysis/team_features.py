import sys
import psycopg2
import pandas as pd
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from config import DB_CONFIG
from analysis.pokemon_data import (
    get_weaknesses, get_base_stat, get_types, get_abilities, ALL_TYPES
)

OUTPUT_DIR = Path(__file__).parent.parent / "output"

# --- Role inference from species data ---

WEATHER_SETTERS = {
    "Pelipper", "Politoed", "Torkoal", "Ninetales", "Ninetales-Alola",
    "Tyranitar", "Hippowdon", "Gigalith", "Baxcalibur"
}

ROCKS_SETTERS = {
    "Great Tusk", "Glimmora", "Garchomp", "Ting-Lu", "Landorus-Therian",
    "Deoxys-Speed", "Gholdengo", "Corviknight", "Skarmory"
}

HAZARD_REMOVERS = {
    "Great Tusk", "Corviknight", "Dragapult", "Iron Treads",
    "Mandibuzz", "Mortalon", "Terapagos"
}

SETUP_MOVES = {"Swords Dance", "Nasty Plot", "Dragon Dance", "Calm Mind", "Quiver Dance"}
PRIORITY_MOVES = {"Extreme Speed", "Sucker Punch", "Bullet Punch", "Aqua Jet", "Shadow Sneak"}
PIVOT_MOVES = {"U-turn", "Volt Switch", "Flip Turn", "Parting Shot"}
TRICK_ROOM_MOVES = {"Trick Room"}


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def fetch_teams_with_moves(conn):
    """Fetch all teams with their Pokémon and observed moves."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            t.team_id,
            t.result,
            p.name        AS pokemon,
            m.name        AS move
        FROM teams t
        JOIN pokemon p ON p.team_id = t.team_id
        LEFT JOIN moves m ON m.pokemon_id = p.pokemon_id
        ORDER BY t.team_id, p.pokemon_id, m.move_slot
    """)
    rows = cursor.fetchall()

    teams = {}
    for team_id, result, pokemon, move in rows:
        if team_id not in teams:
            teams[team_id] = {"result": result, "pokemon": {}}
        if pokemon not in teams[team_id]["pokemon"]:
            teams[team_id]["pokemon"][pokemon] = []
        if move:
            teams[team_id]["pokemon"][pokemon].append(move)

    return list(teams.items())  # [(team_id, {result, pokemon})]


def compute_defensive_profile(pokemon_list: list[str]) -> dict:
    """
    For each type, sum the effectiveness multipliers across all 6 Pokémon.
    Higher = team is more exposed to that type.
    """
    profile = {t: 0.0 for t in ALL_TYPES}
    for name in pokemon_list:
        weaknesses = get_weaknesses(name)
        for t, multiplier in weaknesses.items():
            profile[t] += multiplier
    return {f"def_{t.lower()}": round(v, 2) for t, v in profile.items()}


def compute_offensive_coverage(pokemon_list: list[str]) -> dict:
    """
    For each type, flag whether any Pokémon on the team has STAB of that type.
    1 = team has at least one STAB user of this type, 0 = not covered.
    """
    covered = set()
    for name in pokemon_list:
        for t in get_types(name):
            covered.add(t)
    return {f"stab_{t.lower()}": int(t in covered) for t in ALL_TYPES}


def compute_speed_features(pokemon_list: list[str]) -> dict:
    speeds = []
    for name in pokemon_list:
        spe = get_base_stat(name, "spe")
        if spe is not None:
            speeds.append(spe)
    return {
        "avg_base_speed": round(sum(speeds) / len(speeds), 1) if speeds else 0.0,
        "max_base_speed": max(speeds) if speeds else 0,
        "min_base_speed": min(speeds) if speeds else 0,
    }


def compute_role_flags(pokemon_list: list[str], moves_by_pokemon: dict) -> dict:
    all_observed_moves = set()
    for moves in moves_by_pokemon.values():
        all_observed_moves.update(moves)

    return {
        # Inferred from species
        "has_weather_setter":   int(any(p in WEATHER_SETTERS for p in pokemon_list)),
        "has_rocks_setter":     int(any(p in ROCKS_SETTERS for p in pokemon_list)),
        "has_hazard_remover":   int(any(p in HAZARD_REMOVERS for p in pokemon_list)),

        # Observed from moves in this specific battle
        "setup_observed":       int(bool(all_observed_moves & SETUP_MOVES)),
        "priority_observed":    int(bool(all_observed_moves & PRIORITY_MOVES)),
        "pivot_observed":       int(bool(all_observed_moves & PIVOT_MOVES)),
        "trick_room_observed":  int(bool(all_observed_moves & TRICK_ROOM_MOVES)),
    }


def compute_team_vector(team_id: int, team_data: dict) -> dict:
    pokemon_list = list(team_data["pokemon"].keys())
    moves_by_pokemon = team_data["pokemon"]

    vector = {
        "team_id": team_id,
        "result": team_data["result"],
        "team_size": len(pokemon_list),
    }

    vector.update(compute_defensive_profile(pokemon_list))
    vector.update(compute_offensive_coverage(pokemon_list))
    vector.update(compute_speed_features(pokemon_list))
    vector.update(compute_role_flags(pokemon_list, moves_by_pokemon))

    return vector

def main():
    conn = get_connection()
    teams = fetch_teams_with_moves(conn)
    conn.close()

    print(f"Computing feature vectors for {len(teams)} teams...")

    vectors = []
    missing = set()
    for team_id, team_data in teams:
        for name in team_data["pokemon"]:
            if not get_types(name):
                missing.add(name)
        vectors.append(compute_team_vector(team_id, team_data))

    if missing:
        print(f"\nWarning: {len(missing)} Pokémon not found in pokedex:")
        for name in sorted(missing):
            print(f"  {name}")

    df = pd.DataFrame(vectors)
    df.to_csv(OUTPUT_DIR / "team_features.csv", index=False)
    df.to_json(OUTPUT_DIR / "team_features.json", orient="records", indent=2)
    print(f"\nExported {len(df)} team vectors to output/team_features.csv")

    # Quick win-rate correlation on defensive profile
    print("\n── Win rate correlation with defensive exposure (top 5) ──")
    df["win"] = (df["result"] == "win").astype(int)
    def_cols = [c for c in df.columns if c.startswith("def_")]
    corr = df[def_cols + ["win"]].corr()["win"].drop("win").sort_values()
    print(corr.head(5).to_string())
    print("...")
    print(corr.tail(5).to_string())



if __name__ == "__main__":
    main()