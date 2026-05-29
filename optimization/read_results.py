"""
optimization/read_results.py

Pretty-prints the best teams and generation history from optimizer_results.json.

Usage:
    python3 optimization/read_results.py
    python3 optimization/read_results.py --top 5
    python3 optimization/read_results.py --output path/to/optimizer_results.json
"""

import json
import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

OUTPUT_DIR = Path(__file__).parent.parent / "output"


def load_results(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def print_team(team: list[str], breakdown: dict = None, rank: int = None):
    label = f"#{rank} " if rank else ""
    print(f"\n  {label}Team:")
    for i, p in enumerate(team, 1):
        print(f"    {i}. {p}")
    if breakdown:
        print(f"\n  Scores:")
        print(f"    Fitness:       {breakdown.get('fitness', '—'):.4f}")
        print(f"    Meta Matchup:  {breakdown.get('meta_matchup', '—'):.4f}  (threat resistance)")
        print(f"    Synergy:       {breakdown.get('synergy', '—'):.4f}  (pair co-occurrence win rate)")
        print(f"    Simulation:    {breakdown.get('simulation', '—'):.4f}  (win rate vs DB teams)")
        if 'viability' in breakdown:
            print(f"    Viability:     {breakdown.get('viability', '—'):.4f}  (meta usage penalty)")


def print_generation_summary(generations: list):
    print("\n" + "=" * 60)
    print("  Generation History")
    print("=" * 60)
    print(f"  {'Gen':>4}  {'Best':>8}  {'Avg':>8}  {'Time(s)':>8}  Best Team")
    print(f"  {'---':>4}  {'----':>8}  {'---':>8}  {'-------':>8}  ---------")
    for g in generations:
        team_str = ", ".join(g["best_team"][:3]) + "..."
        print(f"  {g['generation']:>4}  {g['best_score']:>8.4f}  {g['avg_score']:>8.4f}  {g.get('duration_s', 0):>8.1f}  {team_str}")


def get_all_time_top_n(generations: list, n: int) -> list:
    """Collect the top N unique teams across all generations by fitness score."""
    seen = set()
    candidates = []

    for g in generations:
        for entry in g.get("population", []):
            key = tuple(sorted(entry["team"]))
            if key not in seen:
                seen.add(key)
                candidates.append(entry)

    candidates.sort(key=lambda x: x["fitness"], reverse=True)
    return candidates[:n]


def main():
    parser = argparse.ArgumentParser(description="PokéMeta Optimizer Results Reader")
    parser.add_argument("--top",    type=int, default=5,   help="Number of top teams to display")
    parser.add_argument("--output", type=str, default=None, help="Path to optimizer_results.json")
    parser.add_argument("--history", action="store_true",  help="Show full generation history")
    args = parser.parse_args()

    path = Path(args.output) if args.output else OUTPUT_DIR / "optimizer_results.json"

    if not path.exists():
        print(f"No results file found at {path}")
        print("Run the optimizer first: python3 optimization/team_optimizer.py")
        sys.exit(1)

    results = load_results(path)
    generations = results.get("generations", [])

    if not generations:
        print("No generations found in results file.")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  PokéMeta — Optimizer Results")
    print("=" * 60)
    print(f"  Generations completed: {len(generations)}")
    print(f"  All-time best score:   {results['best_score']:.4f}")

    # All-time best team
    print("\n" + "=" * 60)
    print("  ★ All-Time Best Team")
    print("=" * 60)

    # Find the breakdown for the best team
    best_team = results["best_team"]
    best_breakdown = None
    for g in reversed(generations):
        for entry in g.get("population", []):
            if entry["team"] == best_team:
                best_breakdown = entry
                break
        if best_breakdown:
            break

    print_team(best_team, best_breakdown)

    # Top N teams across all generations
    print("\n" + "=" * 60)
    print(f"  Top {args.top} Unique Teams (all generations)")
    print("=" * 60)

    top_teams = get_all_time_top_n(generations, args.top)
    for i, entry in enumerate(top_teams, 1):
        print_team(entry["team"], entry, rank=i)

    # Generation history
    if args.history or True:  # always show summary
        print_generation_summary(generations)

    # Score trend
    best_scores = [g["best_score"] for g in generations]
    avg_scores  = [g["avg_score"]  for g in generations]
    improvement = best_scores[-1] - best_scores[0]
    print(f"\n  Score improvement over {len(generations)} generations: {improvement:+.4f}")
    print(f"  Starting best: {best_scores[0]:.4f} → Current best: {best_scores[-1]:.4f}")
    print(f"  Starting avg:  {avg_scores[0]:.4f}  → Current avg:  {avg_scores[-1]:.4f}")
    print()


if __name__ == "__main__":
    main()