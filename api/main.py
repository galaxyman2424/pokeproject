from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import json
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))
from analysis.threat_analysis import analyze_threats, threat_score, print_report
from ml.recommender import recommend
from analysis.pokemon_data import get_types, get_base_stat, get_abilities, ALL_TYPES

app = FastAPI(title="PokéMeta API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_DIR = Path(__file__).parent.parent / "output"
DATA_DIR   = Path(__file__).parent.parent / "data"


# ── helpers ───────────────────────────────────────────────────────────────────

def load_json(name):
    with open(OUTPUT_DIR / name) as f:
        return json.load(f)

def load_csv(name):
    return pd.read_csv(OUTPUT_DIR / name)


# ── metagame ──────────────────────────────────────────────────────────────────

@app.get("/meta/usage")
def meta_usage(limit: int = Query(30, ge=1, le=300)):
    df = load_csv("pokemon_usage.csv")
    return df.head(limit).to_dict(orient="records")

@app.get("/meta/pairs")
def meta_pairs(limit: int = Query(20, ge=1, le=100), min_appearances: int = Query(10, ge=1)):
    df = load_csv("pair_cooccurrence.csv")
    df = df[df["co_occurrence_count"] >= min_appearances]
    return df.head(limit).to_dict(orient="records")

@app.get("/meta/triplets")
def meta_triplets(limit: int = Query(20, ge=1, le=100)):
    path = OUTPUT_DIR / "triplet_cooccurrence.csv"
    if not path.exists():
        return []
    df = pd.read_csv(path)
    return df.head(limit).to_dict(orient="records")

@app.get("/meta/tera")
def meta_tera(limit: int = Query(15, ge=1, le=100)):
    df = load_csv("tera_rate.csv")
    return df.head(limit).to_dict(orient="records")

@app.get("/meta/tera/{pokemon}")
def meta_tera_distribution(pokemon: str):
    df = load_csv("tera_type_distribution.csv")
    filtered = df[df["pokemon"].str.lower() == pokemon.lower()]
    if filtered.empty:
        raise HTTPException(404, f"No tera data for {pokemon}")
    return filtered.to_dict(orient="records")

@app.get("/meta/moves/{pokemon}")
def meta_moves(pokemon: str):
    df = load_csv("move_usage.csv")
    filtered = df[df["pokemon"].str.lower() == pokemon.lower()]
    if filtered.empty:
        raise HTTPException(404, f"No move data for {pokemon}")
    return filtered.to_dict(orient="records")


# ── team analysis ─────────────────────────────────────────────────────────────

@app.get("/team/analyze")
def team_analyze(team: str = Query(..., description="Comma-separated Pokémon names")):
    names = [n.strip() for n in team.split(",") if n.strip()]
    if len(names) < 1:
        raise HTTPException(400, "Provide at least 1 Pokémon")
    if len(names) > 6:
        raise HTTPException(400, "Max 6 Pokémon")
    report = analyze_threats(names)
    report["threat_score"] = round(threat_score(report), 4)
    return report

@app.get("/team/recommend")
def team_recommend(
    team: str = Query("", description="Comma-separated current team (can be empty)"),
    n: int = Query(10, ge=1, le=30)
):
    names = [n.strip() for n in team.split(",") if n.strip()] if team else []
    if len(names) > 5:
        raise HTTPException(400, "Max 5 Pokémon for recommendations (need 1 slot)")
    results = recommend(names, n=n, verbose=False)
    return results


# ── optimizer ────────────────────────────────────────────────────────────────

@app.get("/optimizer/results")
def optimizer_results():
    path = OUTPUT_DIR / "optimizer_results.json"
    if not path.exists():
        raise HTTPException(404, "No optimizer results found. Run Phase 5 first.")
    with open(path) as f:
        data = json.load(f)
    return data

@app.get("/optimizer/best")
def optimizer_best(n: int = Query(5, ge=1, le=20)):
    path = OUTPUT_DIR / "optimizer_results.json"
    if not path.exists():
        raise HTTPException(404, "No optimizer results found.")
    with open(path) as f:
        data = json.load(f)
    # Collect all teams across all generations, deduplicate by team composition
    all_teams = []
    seen = set()
    for gen in data.get("generations", []):
        for team_entry in gen.get("teams", []):
            key = tuple(sorted(team_entry.get("team", [])))
            if key not in seen:
                seen.add(key)
                all_teams.append(team_entry)
    all_teams.sort(key=lambda x: x.get("fitness", 0), reverse=True)
    return all_teams[:n]


# ── pokédex ───────────────────────────────────────────────────────────────────

@app.get("/pokemon/{name}")
def pokemon_lookup(name: str):
    types = get_types(name)
    if not types:
        raise HTTPException(404, f"{name} not found in pokédex")
    stats = {s: get_base_stat(name, s) for s in ["hp","atk","def","spa","spd","spe"]}
    abilities = get_abilities(name)
    return {
        "name": name,
        "types": types,
        "base_stats": stats,
        "abilities": abilities,
    }

@app.get("/pokemon/{name}/weaknesses")
def pokemon_weaknesses(name: str):
    from analysis.pokemon_data import get_weaknesses
    types = get_types(name)
    if not types:
        raise HTTPException(404, f"{name} not found")
    return get_weaknesses(name)