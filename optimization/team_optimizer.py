"""
optimization/team_optimizer.py

Genetic algorithm optimizer for competitive Pokémon team building.

Fitness function:
    fitness = 0.4 * meta_matchup       (1.0 - threat_score from threat_analysis)
            + 0.3 * synergy_score      (pair co-occurrence win rates from Phase 2)
            + 0.3 * simulation_score   (win rate vs sampled DB teams from Phase 6)

Usage:
    python3 optimization/team_optimizer.py
    python3 optimization/team_optimizer.py --generations 20 --population 30 --battles 10
"""

import json
import random
import argparse
import psycopg2
import sys
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.append(str(Path(__file__).parent.parent))

from config import DB_CONFIG
from analysis.pokemon_data import get_types
from analysis.threat_analysis import analyze_threats, threat_score
from simulation.simulation_runner import simulate_matchup

DATA_DIR   = Path(__file__).parent.parent / "data"
OUTPUT_DIR = Path(__file__).parent.parent / "output"


# ── Constants ─────────────────────────────────────────────────────────────────

MUTATION_RATE   = 0.3   # probability of mutating each team after crossover
TOURNAMENT_SIZE = 4     # number of candidates in each tournament selection
META_SAMPLE_SIZE = 8    # number of DB teams to sample per fitness evaluation
BATTLES_PER_MATCHUP = 5 # battles per opponent during simulation (overridden by CLI)


# ── Data loading ──────────────────────────────────────────────────────────────

def load_ou_pool() -> list[str]:
    """
    Load the OU-legal Pokémon pool from data/ou_pool.json.
    Filter to species that exist in pokedex.json to avoid broken formes.
    """
    pool_path = DATA_DIR / "ou_pool.json"
    dex_path  = DATA_DIR / "pokedex.json"

    with open(pool_path) as f:
        pool = json.load(f)
    with open(dex_path) as f:
        dex = json.load(f)

    valid = [name for name in pool if name in dex]
    print(f"[pool] Loaded {len(valid)} valid OU-legal species.")
    return valid


def load_pair_cooccurrence() -> dict[tuple, float]:
    """
    Load pair win rates from output/pair_cooccurrence.json.
    Returns {(pokemon_a, pokemon_b): win_rate} for quick synergy lookup.
    """
    path = OUTPUT_DIR / "pair_cooccurrence.json"
    if not path.exists():
        print("[synergy] pair_cooccurrence.json not found — synergy score will be 0.5 baseline.")
        return {}

    with open(path) as f:
        records = json.load(f)

    pairs = {}
    for r in records:
        key = tuple(sorted([r["pokemon_a"], r["pokemon_b"]]))
        pairs[key] = r["pair_win_rate"] / 100.0  # normalize to 0.0–1.0
    return pairs


def sample_meta_teams(n: int, conn) -> list[list[str]]:
    """
    Sample n random teams from the database.
    Returns a list of 6-Pokémon name lists.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.team_id
        FROM teams t
        ORDER BY RANDOM()
        LIMIT %s
    """, (n,))
    team_ids = [row[0] for row in cursor.fetchall()]

    teams = []
    for team_id in team_ids:
        cursor.execute("""
            SELECT p.name FROM pokemon p
            WHERE p.team_id = %s
            ORDER BY p.pokemon_id
        """, (team_id,))
        names = [row[0] for row in cursor.fetchall()]
        if len(names) == 6:
            teams.append(names)

    return teams


# ── Team generation ───────────────────────────────────────────────────────────

def random_team(pool: list[str]) -> list[str]:
    """Draw 6 unique Pokémon from the pool."""
    return random.sample(pool, 6)


# ── Fitness components ────────────────────────────────────────────────────────

def meta_matchup_score(team: list[str]) -> float:
    """
    1.0 - threat_score. Higher is better.
    threat_score is 0.0–1.0 where lower means fewer threats.
    """
    try:
        report = analyze_threats(team)
        return round(1.0 - threat_score(report), 4)
    except Exception as e:
        print(f"[fitness] threat analysis failed for {team}: {e}")
        return 0.5


def synergy_score(team: list[str], pair_data: dict) -> float:
    """
    Average pair win rate across all C(6,2)=15 pairs on the team.
    Pairs not in the dataset default to 0.5 (neutral).
    """
    from itertools import combinations
    scores = []
    for a, b in combinations(sorted(team), 2):
        key = tuple(sorted([a, b]))
        scores.append(pair_data.get(key, 0.5))
    return round(sum(scores) / len(scores), 4) if scores else 0.5


def simulation_score(team: list[str], meta_teams: list[list[str]], n_battles: int) -> float:
    """
    Win rate against sampled meta teams via the Showdown battle engine.
    Returns 0.0–1.0.
    """
    if not meta_teams:
        return 0.5

    total_wins = 0
    total_battles = 0

    for opponent in meta_teams:
        try:
            result = simulate_matchup(
                team_a=team,
                team_b=opponent,
                n_battles=n_battles,
                verbose=False,
            )
            total_wins    += result["team_a_wins"]
            total_battles += result["battles"]
        except Exception as e:
            print(f"[sim] matchup failed: {e}")

    return round(total_wins / total_battles, 4) if total_battles > 0 else 0.5


def fitness(
    team: list[str],
    pair_data: dict,
    meta_teams: list[list[str]],
    n_battles: int,
    weights: dict,
) -> tuple[float, dict]:
    """
    Compute composite fitness score for a team.

    Returns:
        (score, breakdown_dict)
    """
    mm  = meta_matchup_score(team)
    syn = synergy_score(team, pair_data)
    sim = simulation_score(team, meta_teams, n_battles)

    score = (
        weights["meta_matchup"]  * mm  +
        weights["synergy"]       * syn +
        weights["simulation"]    * sim
    )

    breakdown = {
        "meta_matchup":   mm,
        "synergy":        syn,
        "simulation":     sim,
        "fitness":        round(score, 4),
    }
    return round(score, 4), breakdown


# ── Genetic operators ─────────────────────────────────────────────────────────

def tournament_select(population: list, scores: list[float], k: int = TOURNAMENT_SIZE) -> list[str]:
    """
    Pick k candidates at random, return the one with the highest fitness.
    """
    indices   = random.sample(range(len(population)), min(k, len(population)))
    best_idx  = max(indices, key=lambda i: scores[i])
    return population[best_idx]


def crossover(team_a: list[str], team_b: list[str]) -> list[str]:
    """
    Preserve a random core of 3 Pokémon from team_a (the higher-scoring parent).
    Fill remaining 3 slots with Pokémon from team_b not already in the core.
    If team_b can't fill all slots, draw from team_a's remainder.
    """
    core = random.sample(team_a, 3)
    fill = [p for p in team_b if p not in core]

    # If team_b doesn't provide 3 unique non-core members, pull from team_a remainder
    if len(fill) < 3:
        remainder = [p for p in team_a if p not in core]
        fill += [p for p in remainder if p not in fill]

    child = core + fill[:3]

    # Safety: deduplicate (shouldn't happen but be defensive)
    seen = []
    for p in child:
        if p not in seen:
            seen.append(p)
    return seen[:6]


def mutate(team: list[str], pool: list[str], rate: float = MUTATION_RATE) -> list[str]:
    """
    With probability `rate`, replace one random Pokémon with a random pool member
    not already on the team.
    """
    if random.random() > rate:
        return team

    available = [p for p in pool if p not in team]
    if not available:
        return team

    idx         = random.randint(0, 5)
    replacement = random.choice(available)
    new_team    = team[:]
    new_team[idx] = replacement
    return new_team


# ── Results I/O ───────────────────────────────────────────────────────────────

def save_results(results: dict, path: Path):
    path.write_text(json.dumps(results, indent=2))
    print(f"[output] Saved results to {path}")


def load_results(path: Path) -> dict:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"generations": [], "best_team": None, "best_score": 0.0}


# ── Main optimizer loop ───────────────────────────────────────────────────────

def run_optimizer(
    generations:     int   = 10,
    population_size: int   = 30,
    n_battles:       int   = BATTLES_PER_MATCHUP,
    meta_sample:     int   = META_SAMPLE_SIZE,
    weights:         dict  = None,
    output_path:     Path  = None,
    resume:          bool  = True,
):
    if weights is None:
        weights = {"meta_matchup": 0.4, "synergy": 0.3, "simulation": 0.3}

    if output_path is None:
        output_path = OUTPUT_DIR / "optimizer_results.json"

    print("\n" + "=" * 60)
    print("  PokéMeta — Genetic Team Optimizer")
    print("=" * 60)
    print(f"  Generations:     {generations}")
    print(f"  Population size: {population_size}")
    print(f"  Battles/matchup: {n_battles}")
    print(f"  Meta sample:     {meta_sample} opponent teams")
    print(f"  Weights:         {weights}")
    print(f"  Output:          {output_path}")
    print("=" * 60 + "\n")

    # Load persistent data
    pool      = load_ou_pool()
    pair_data = load_pair_cooccurrence()

    # Load previous results if resuming
    results = load_results(output_path) if resume else {"generations": [], "best_team": None, "best_score": 0.0}
    start_gen = len(results["generations"]) + 1

    # DB connection for meta team sampling
    conn = psycopg2.connect(**DB_CONFIG)

    # Initialise or restore population
    if results["generations"]:
        # Seed from the best team of the previous run + fresh randoms
        last_gen   = results["generations"][-1]
        best_teams = [entry["team"] for entry in sorted(last_gen["population"], key=lambda x: x["fitness"], reverse=True)[:population_size // 3]]
        population = best_teams + [random_team(pool) for _ in range(population_size - len(best_teams))]
        print(f"[init] Resumed from generation {start_gen - 1}. Seeding {len(best_teams)} elite teams.")
    else:
        population = [random_team(pool) for _ in range(population_size)]
        print(f"[init] Initialised fresh population of {population_size} teams.")

    # Track all-time best
    best_team  = results.get("best_team")
    best_score = results.get("best_score", 0.0)

    for gen in range(start_gen, start_gen + generations):
        gen_start = datetime.now()
        print(f"\n── Generation {gen} ──────────────────────────────────────")

        # Sample a fresh set of meta opponents for this generation
        meta_teams = sample_meta_teams(meta_sample, conn)
        print(f"[gen {gen}] Sampled {len(meta_teams)} meta opponent teams.")

        # Evaluate fitness for every team in the population
        scores     = []
        breakdowns = []

        for i, team in enumerate(population):
            score, breakdown = fitness(team, pair_data, meta_teams, n_battles, weights)
            scores.append(score)
            breakdowns.append(breakdown)
            print(f"  [{i+1:2}/{population_size}] {team} → {score:.4f}  "
                  f"(mm={breakdown['meta_matchup']:.2f} syn={breakdown['synergy']:.2f} sim={breakdown['simulation']:.2f})")

        # Track best
        gen_best_idx = max(range(len(scores)), key=lambda i: scores[i])
        gen_best_score = scores[gen_best_idx]
        gen_best_team  = population[gen_best_idx]

        if gen_best_score > best_score:
            best_score = gen_best_score
            best_team  = gen_best_team
            print(f"\n  ★ New all-time best: {best_team} ({best_score:.4f})")

        # Record generation
        gen_record = {
            "generation": gen,
            "best_score": gen_best_score,
            "best_team":  gen_best_team,
            "avg_score":  round(sum(scores) / len(scores), 4),
            "duration_s": round((datetime.now() - gen_start).total_seconds(), 1),
            "population": [
                {"team": team, **bd}
                for team, bd in zip(population, breakdowns)
            ],
        }
        results["generations"].append(gen_record)
        results["best_team"]  = best_team
        results["best_score"] = best_score

        # Save after every generation so overnight runs don't lose progress
        save_results(results, output_path)

        # Build next generation
        next_population = []

        # Elitism — carry top 10% directly into next generation unchanged
        elite_count = max(1, population_size // 10)
        elite_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:elite_count]
        for idx in elite_indices:
            next_population.append(population[idx])

        # Fill rest via selection → crossover → mutation
        while len(next_population) < population_size:
            parent_a = tournament_select(population, scores)
            parent_b = tournament_select(population, scores)
            child    = crossover(parent_a, parent_b)
            child    = mutate(child, pool)
            # Ensure team has 6 members (defensive check)
            if len(child) == 6:
                next_population.append(child)

        population = next_population

        elapsed = (datetime.now() - gen_start).total_seconds()
        print(f"\n[gen {gen}] Done. Best this gen: {gen_best_score:.4f} | All-time best: {best_score:.4f} | Time: {elapsed:.1f}s")

    conn.close()

    print("\n" + "=" * 60)
    print("  Optimization complete.")
    print(f"  Best team:  {best_team}")
    print(f"  Best score: {best_score:.4f}")
    print(f"  Results:    {output_path}")
    print("=" * 60)

    return best_team, best_score


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PokéMeta Genetic Team Optimizer")
    parser.add_argument("--generations",  type=int,   default=10,    help="Number of generations to run")
    parser.add_argument("--population",   type=int,   default=30,    help="Population size")
    parser.add_argument("--battles",      type=int,   default=5,     help="Battles per matchup during simulation")
    parser.add_argument("--meta-sample",  type=int,   default=8,     help="Number of DB teams to sample per generation")
    parser.add_argument("--no-resume",    action="store_true",        help="Start fresh instead of resuming previous run")
    parser.add_argument("--output",       type=str,   default=None,  help="Path to output JSON file")
    parser.add_argument("--mm-weight",    type=float, default=0.4,   help="Weight for meta matchup score")
    parser.add_argument("--syn-weight",   type=float, default=0.3,   help="Weight for synergy score")
    parser.add_argument("--sim-weight",   type=float, default=0.3,   help="Weight for simulation score")
    args = parser.parse_args()

    weights = {
        "meta_matchup": args.mm_weight,
        "synergy":      args.syn_weight,
        "simulation":   args.sim_weight,
    }

    # Normalize weights in case they don't sum to 1.0
    total = sum(weights.values())
    weights = {k: round(v / total, 4) for k, v in weights.items()}

    output_path = Path(args.output) if args.output else None

    run_optimizer(
        generations=args.generations,
        population_size=args.population,
        n_battles=args.battles,
        meta_sample=args.meta_sample,
        weights=weights,
        output_path=output_path,
        resume=not args.no_resume,
    )