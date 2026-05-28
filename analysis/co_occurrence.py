import sys
import psycopg2
import pandas as pd
from itertools import combinations
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from config import DB_CONFIG

OUTPUT_DIR = Path(__file__).parent.parent / "output"


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def fetch_teams(conn):
    """Fetch all teams as a list of (team_id, result, [pokemon_names])."""
    cursor = conn.cursor()

    cursor.execute("""
        SELECT t.team_id, t.result, p.name
        FROM teams t
        JOIN pokemon p ON p.team_id = t.team_id
        ORDER BY t.team_id, p.pokemon_id
    """)
    rows = cursor.fetchall()

    teams = {}
    for team_id, result, name in rows:
        if team_id not in teams:
            teams[team_id] = {"result": result, "pokemon": []}
        teams[team_id]["pokemon"].append(name)

    return list(teams.values())


def compute_pair_cooccurrence(teams):
    """Compute co-occurrence stats for all Pokémon pairs."""
    total_teams = len(teams)
    pair_counts = {}
    pair_wins = {}

    for team in teams:
        pokemon = team["pokemon"]
        result = team["result"]
        won = result == "win"

        for a, b in combinations(sorted(pokemon), 2):
            key = (a, b)
            pair_counts[key] = pair_counts.get(key, 0) + 1
            if won:
                pair_wins[key] = pair_wins.get(key, 0) + 1

    records = []
    for (a, b), count in pair_counts.items():
        wins = pair_wins.get((a, b), 0)
        records.append({
            "pokemon_a": a,
            "pokemon_b": b,
            "co_occurrence_count": count,
            "co_occurrence_rate": round(count * 100.0 / total_teams, 2),
            "pair_win_count": wins,
            "pair_win_rate": round(wins * 100.0 / count, 2),
        })

    df = pd.DataFrame(records)
    df = df.sort_values("co_occurrence_count", ascending=False).reset_index(drop=True)
    return df


def compute_triplet_cooccurrence(teams, min_count=5):
    """Compute co-occurrence stats for Pokémon triplets (filtered to min_count)."""
    total_teams = len(teams)
    triplet_counts = {}
    triplet_wins = {}

    for team in teams:
        pokemon = team["pokemon"]
        result = team["result"]
        won = result == "win"

        for trio in combinations(sorted(pokemon), 3):
            triplet_counts[trio] = triplet_counts.get(trio, 0) + 1
            if won:
                triplet_wins[trio] = triplet_wins.get(trio, 0) + 1

    records = []
    for trio, count in triplet_counts.items():
        if count < min_count:
            continue
        wins = triplet_wins.get(trio, 0)
        records.append({
            "pokemon_a": trio[0],
            "pokemon_b": trio[1],
            "pokemon_c": trio[2],
            "co_occurrence_count": count,
            "co_occurrence_rate": round(count * 100.0 / total_teams, 2),
            "pair_win_count": wins,
            "pair_win_rate": round(wins * 100.0 / count, 2),
        })

    df = pd.DataFrame(records)
    df = df.sort_values("co_occurrence_count", ascending=False).reset_index(drop=True)
    return df


def print_summary(pair_df, triplet_df):
    print("\n══════════════════════════════════════════")
    print("  TOP 20 PAIRS BY CO-OCCURRENCE")
    print("══════════════════════════════════════════")
    print(pair_df.head(20).to_string(index=False))

    print("\n══════════════════════════════════════════")
    print("  TOP 20 PAIRS BY WIN RATE (min 10 appearances)")
    print("══════════════════════════════════════════")
    strong = pair_df[pair_df["co_occurrence_count"] >= 10].sort_values(
        "pair_win_rate", ascending=False
    )
    print(strong.head(20).to_string(index=False))

    print("\n══════════════════════════════════════════")
    print("  TOP TRIPLET CORES (min 5 appearances)")
    print("══════════════════════════════════════════")
    if triplet_df.empty:
        print("  Not enough data for triplet analysis — consider ingesting more replays.")
    else:
        print(triplet_df.head(20).to_string(index=False))


def main():
    conn = get_connection()
    teams = fetch_teams(conn)
    conn.close()

    print(f"Loaded {len(teams)} teams.")

    pair_df = compute_pair_cooccurrence(teams)
    triplet_df = compute_triplet_cooccurrence(teams, min_count=5)

    print_summary(pair_df, triplet_df)

    pair_df.to_csv(OUTPUT_DIR / "pair_cooccurrence.csv", index=False)
    pair_df.to_json(OUTPUT_DIR / "pair_cooccurrence.json", orient="records", indent=2)

    if not triplet_df.empty:
        triplet_df.to_csv(OUTPUT_DIR / "triplet_cooccurrence.csv", index=False)
        triplet_df.to_json(OUTPUT_DIR / "triplet_cooccurrence.json", orient="records", indent=2)

    print(f"\nExported co-occurrence data to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()