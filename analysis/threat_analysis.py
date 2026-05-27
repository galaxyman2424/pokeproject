import sys
import pandas as pd
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from analysis.pokemon_data import get_weaknesses, get_base_stat, get_types, ALL_TYPES

OUTPUT_DIR = Path(__file__).parent.parent / "output"

# --- Static game knowledge ---

WEATHER_SETTERS = {
    "Pelipper", "Politoed", "Torkoal", "Ninetales", "Ninetales-Alola",
    "Tyranitar", "Hippowdon", "Gigalith", "Baxcalibur"
}

RAIN_ABUSERS = {
    "Kingdra", "Barraskewda", "Araquanid", "Swampert", "Ludicolo",
    "Iron Bundle", "Floatzel"
}

SUN_ABUSERS = {
    "Walking Wake", "Venusaur", "Lilligant", "Charizard", "Entei"
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


# --- Dynamic meta data (loaded at runtime from Phase 2 output) ---

def load_meta_threats(top_n: int = 20) -> list[dict]:
    path = OUTPUT_DIR / "pokemon_usage.csv"
    if not path.exists():
        return []
    df = pd.read_csv(path).head(top_n)
    threats = []
    for _, row in df.iterrows():
        name = row["name"]
        types = get_types(name)
        speed = get_base_stat(name, "spe") or 0
        threats.append({"name": name, "types": types, "speed": speed})
    return threats


def load_speed_tiers(top_n: int = 20) -> dict[str, int]:
    path = OUTPUT_DIR / "pokemon_usage.csv"
    if not path.exists():
        return {}
    df = pd.read_csv(path).head(top_n)
    tiers = {}
    for _, row in df.iterrows():
        name = row["name"]
        speed = get_base_stat(name, "spe")
        if speed is not None:
            tiers[name] = speed
    return dict(sorted(tiers.items(), key=lambda x: x[1], reverse=True))


# --- Analysis functions ---

def defensive_profile(pokemon_list: list[str]) -> dict[str, float]:
    profile = {t: 0.0 for t in ALL_TYPES}
    for name in pokemon_list:
        for t, mult in get_weaknesses(name).items():
            profile[t] += mult
    return profile


def offensive_stab_coverage(pokemon_list: list[str]) -> set[str]:
    covered = set()
    for name in pokemon_list:
        for t in get_types(name):
            covered.add(t)
    return covered


def find_type_holes(pokemon_list: list[str], threshold: float = 8.0) -> list[dict]:
    profile = defensive_profile(pokemon_list)
    stab = offensive_stab_coverage(pokemon_list)
    holes = []
    for t, exposure in profile.items():
        if exposure >= threshold and t not in stab:
            holes.append({"type": t, "exposure": round(exposure, 2)})
    holes.sort(key=lambda x: x["exposure"], reverse=True)
    return holes


def find_speed_gaps(pokemon_list: list[str]) -> dict:
    speeds = [get_base_stat(n, "spe") for n in pokemon_list if get_base_stat(n, "spe")]
    max_speed = max(speeds) if speeds else 0
    min_speed = min(speeds) if speeds else 0
    avg_speed = round(sum(speeds) / len(speeds), 1) if speeds else 0

    tiers = load_speed_tiers()
    outsped_by = [name for name, spd in tiers.items() if spd > max_speed]

    return {
        "max_speed": max_speed,
        "min_speed": min_speed,
        "avg_speed": avg_speed,
        "outsped_by": outsped_by
    }


def find_role_gaps(pokemon_list: list[str]) -> list[str]:
    gaps = []
    if not any(p in HAZARD_REMOVERS for p in pokemon_list):
        gaps.append("no_hazard_removal")
    if not any(p in ROCKS_SETTERS for p in pokemon_list):
        gaps.append("no_stealth_rock")
    has_weather = any(p in WEATHER_SETTERS for p in pokemon_list)
    has_rain_abuser = any(p in RAIN_ABUSERS for p in pokemon_list)
    has_sun_abuser = any(p in SUN_ABUSERS for p in pokemon_list)
    if (has_rain_abuser or has_sun_abuser) and not has_weather:
        gaps.append("weather_abuser_without_setter")
    return gaps


def meta_coverage_score(pokemon_list: list[str]) -> dict:
    threats = load_meta_threats()
    stab = offensive_stab_coverage(pokemon_list)
    uncovered = []
    for threat in threats:
        if not any(t in stab for t in threat["types"]):
            uncovered.append(threat["name"])
    score = len(threats) - len(uncovered)
    return {"score": score, "total": len(threats), "uncovered": uncovered}


def archetype_weakness_flags(pokemon_list: list[str]) -> dict:
    profile = defensive_profile(pokemon_list)
    stab = offensive_stab_coverage(pokemon_list)
    has_weather = any(p in WEATHER_SETTERS for p in pokemon_list)

    # Weak to rain: high Water exposure, no Electric/Grass STAB, not a rain team
    weak_to_rain = (
        profile.get("Water", 0) >= 8.0
        and "Electric" not in stab
        and "Grass" not in stab
        and not has_weather
    )

    # Weak to sun: high Fire exposure, no Water/Rock STAB
    weak_to_sun = (
        profile.get("Fire", 0) >= 8.0
        and "Water" not in stab
        and "Rock" not in stab
    )

    # Weak to HO: slow team with no hazard removal
    speeds = [get_base_stat(n, "spe") for n in pokemon_list if get_base_stat(n, "spe")]
    avg_speed = sum(speeds) / len(speeds) if speeds else 0
    weak_to_ho = (
        avg_speed < 70
        and not any(p in HAZARD_REMOVERS for p in pokemon_list)
    )

    return {
        "weak_to_rain": int(weak_to_rain),
        "weak_to_sun": int(weak_to_sun),
        "weak_to_ho": int(weak_to_ho),
    }


def threat_score(report: dict) -> float:
    score = 0.0
    # Type holes — up to 0.3
    holes = report["type_holes"]
    score += min(len(holes) * 0.075, 0.3)
    # Role gaps — up to 0.2
    gaps = report["role_gaps"]
    score += min(len(gaps) * 0.1, 0.2)
    # Meta coverage — up to 0.3
    mc = report["meta_coverage"]
    if mc["total"] > 0:
        uncovered_ratio = len(mc["uncovered"]) / mc["total"]
        score += uncovered_ratio * 0.3
    # Archetype flags — up to 0.1
    flags = report["archetype_flags"]
    score += sum(flags.values()) * 0.033
    # Speed gaps — up to 0.1
    outsped = len(report["speed_gaps"]["outsped_by"])
    score += min(outsped * 0.02, 0.1)
    return round(min(score, 1.0), 4)


def analyze_threats(pokemon_list: list[str]) -> dict:
    report = {
        "team": pokemon_list,
        "type_holes": find_type_holes(pokemon_list),
        "speed_gaps": find_speed_gaps(pokemon_list),
        "role_gaps": find_role_gaps(pokemon_list),
        "meta_coverage": meta_coverage_score(pokemon_list),
        "archetype_flags": archetype_weakness_flags(pokemon_list),
    }
    report["threat_score"] = threat_score(report)
    return report


def print_report(report: dict):
    print("\n══════════════════════════════════════════")
    print("  THREAT ANALYSIS REPORT")
    print("══════════════════════════════════════════")
    print(f"Team: {', '.join(report['team'])}")
    print(f"\nThreat Score: {report['threat_score']} (lower = better)")

    print("\n── Type Holes ──")
    if report["type_holes"]:
        for h in report["type_holes"]:
            print(f"  {h['type']}: exposure {h['exposure']}")
    else:
        print("  None")

    print("\n── Speed Gaps ──")
    sg = report["speed_gaps"]
    print(f"  Max: {sg['max_speed']}  Min: {sg['min_speed']}  Avg: {sg['avg_speed']}")
    if sg["outsped_by"]:
        print(f"  Outsped by: {', '.join(sg['outsped_by'])}")

    print("\n── Role Gaps ──")
    if report["role_gaps"]:
        for g in report["role_gaps"]:
            print(f"  {g}")
    else:
        print("  None")

    print("\n── Meta Coverage ──")
    mc = report["meta_coverage"]
    print(f"  Score: {mc['score']}/{mc['total']}")
    if mc["uncovered"]:
        print(f"  Uncovered: {', '.join(mc['uncovered'])}")

    print("\n── Archetype Flags ──")
    for flag, val in report["archetype_flags"].items():
        print(f"  {flag}: {'YES' if val else 'no'}")


if __name__ == "__main__":
    test_team = [
        "Great Tusk", "Gholdengo", "Kingambit",
        "Dragonite", "Hatterene", "Corviknight"
    ]
    report = analyze_threats(test_team)
    print_report(report)