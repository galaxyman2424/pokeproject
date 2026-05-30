"""
ml/recommender.py

Team recommendation system.
Given a partial team, scores all candidate Pokémon from the OU pool
and returns ranked suggestions with a score breakdown.

Usage:
    cd ~/pokeproject
    python3 ml/recommender.py
"""

import sys
import json
import numpy as np
import pandas as pd
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from analysis.threat_analysis import analyze_threats, threat_score
from analysis.pokemon_data import get_types

OUTPUT_DIR = Path(__file__).parent.parent / "output"
DATA_DIR   = Path(__file__).parent.parent / "data"


# ── Data loading ──────────────────────────────────────────────────────────────

def load_pair_cooccurrence():
    path = OUTPUT_DIR / "pair_cooccurrence.json"
    df   = pd.read_json(path)
    lookup = {}
    for _, row in df.iterrows():
        if row["co_occurrence_count"] < 5:
            continue
        a, b = row["pokemon_a"], row["pokemon_b"]
        wr   = row["pair_win_rate"] / 100.0
        lookup[(a, b)] = wr
        lookup[(b, a)] = wr
    return lookup

def load_usage():
    df      = pd.read_csv(OUTPUT_DIR / "pokemon_usage.csv")
    max_use = df["usage_pct"].max()
    return {
        row["name"]: (row["usage_pct"] / max_use) ** 0.5
        for _, row in df.iterrows()
    }

def load_ou_pool():
    with open(DATA_DIR / "ou_pool.json") as f:
        return json.load(f)


# ── Scoring components ────────────────────────────────────────────────────────

def synergy_score(candidate, current_team, pair_lookup):
    if not current_team:
        return 0.5
    rates = []
    for member in current_team:
        key = (candidate, member)
        rates.append(pair_lookup.get(key, 0.5))
    return sum(rates) / len(rates)


def threat_improvement_score(candidate, current_team):
    if not current_team:
        base = 0.5
    else:
        base = threat_score(analyze_threats(current_team))

    new_team    = current_team + [candidate]
    new_score   = threat_score(analyze_threats(new_team))
    improvement = base - new_score  # positive = candidate reduces threats
    # Normalize to 0-1 range (improvement typically -0.3 to +0.3)
    return max(0.0, min(1.0, 0.5 + improvement * 2.0))


def diversity_score(candidate, current_team):
    if not current_team:
        return 1.0
    candidate_types = set(get_types(candidate))
    if not candidate_types:
        return 0.5
    overlap_count = 0
    for member in current_team:
        member_types = set(get_types(member))
        if candidate_types & member_types:
            overlap_count += 1
    overlap_rate = overlap_count / len(current_team)
    return 1.0 - overlap_rate


# ── Main recommendation function ──────────────────────────────────────────────

def recommend(
    current_team: list[str],
    n: int = 5,
    weights: dict | None = None,
    verbose: bool = True,
) -> list[dict]:
    if weights is None:
        weights = {
            "synergy":     0.4,
            "threat":      0.3,
            "usage":       0.2,
            "diversity":   0.1,
        }

    pair_lookup = load_pair_cooccurrence()
    usage_map   = load_usage()
    ou_pool     = load_ou_pool()

    # Filter out Pokémon already on the team
    candidates = [p for p in ou_pool if p not in current_team]

    if verbose:
        slots_remaining = 6 - len(current_team)
        print(f"\nCurrent team  : {current_team}")
        print(f"Slots remaining: {slots_remaining}")
        print(f"Scoring {len(candidates)} candidates...\n")

    results = []
    for candidate in candidates:
        syn  = synergy_score(candidate, current_team, pair_lookup)
        thr  = threat_improvement_score(candidate, current_team)
        use  = usage_map.get(candidate, 0.1)
        div  = diversity_score(candidate, current_team)

        composite = (
            weights["synergy"]   * syn  +
            weights["threat"]    * thr  +
            weights["usage"]     * use  +
            weights["diversity"] * div
        )

        results.append({
            "pokemon":           candidate,
            "composite":         round(composite, 4),
            "synergy":           round(syn, 4),
            "threat_improvement":round(thr, 4),
            "usage":             round(use, 4),
            "diversity":         round(div, 4),
        })

    results.sort(key=lambda x: x["composite"], reverse=True)
    return results[:n]


def print_recommendations(recommendations, current_team):
    print(f"{'='*60}")
    print(f"  TOP RECOMMENDATIONS")
    print(f"  Current team: {', '.join(current_team) if current_team else '(empty)'}")
    print(f"{'='*60}")
    print(f"  {'#':<3} {'Pokémon':<22} {'Score':<7} {'Syn':<7} {'Threat':<8} {'Usage':<7} {'Div'}")
    print(f"  {'-'*57}")
    for i, r in enumerate(recommendations, 1):
        print(
            f"  {i:<3} {r['pokemon']:<22} {r['composite']:<7} "
            f"{r['synergy']:<7} {r['threat_improvement']:<8} "
            f"{r['usage']:<7} {r['diversity']}"
        )


# ── Test cases ────────────────────────────────────────────────────────────────

def main():
    # Test 1: Empty team (cold start)
    recs = recommend([], n=10, verbose=True)
    print_recommendations(recs, [])

    # Test 2: Classic balance core — what rounds it out?
    core = ["Great Tusk", "Gholdengo", "Kingambit"]
    recs = recommend(core, n=10, verbose=True)
    print_recommendations(recs, core)

    # Test 3: Rain core — fill the remaining slots
    rain = ["Pelipper", "Kingdra", "Araquanid"]
    recs = recommend(rain, n=10, verbose=True)
    print_recommendations(recs, rain)

    # Test 4: Nearly full team — one slot left
    team = ["Great Tusk", "Gholdengo", "Kingambit", "Dragonite", "Corviknight"]
    recs = recommend(team, n=5, verbose=True)
    print_recommendations(recs, team)


if __name__ == "__main__":
    main()