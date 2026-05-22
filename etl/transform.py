from pathlib import Path
from typing import Dict

def parse_log(file_path: str) -> Dict:
    """Parse a raw Showdown .log file into a structured dictionary."""
    
    battle = {
        "battle_id": Path(file_path).stem,
        "format": None,
        "winner": None,
        "loser": None,
        "players": {},
        "teams": {"p1": [], "p2": []},
        "actions": []
    }

    current_turn = 0

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or not line.startswith("|"):
                continue
            
            parts = line.split("|")
            # parts[0] is always empty string due to leading |
            tag = parts[1] if len(parts) > 1 else ""

            # --- Battle metadata ---
            if tag == "tier":
                battle["format"] = parts[2]

            elif tag == "player":
                # |player|p1|ethanolli1|avatar|elo
                pid = parts[2]      # p1 or p2
                name = parts[3]
                battle["players"][pid] = name

            # --- Team composition ---
            elif tag == "poke":
                # |poke|p1|Landorus-Therian, M|
                pid = parts[2]
                raw = parts[3].split(",")[0].strip()  # just the name, no gender
                battle["teams"][pid].append(raw)

            # --- Turn tracking ---
            elif tag == "turn":
                current_turn = int(parts[2])

            # --- Switches ---
            elif tag == "switch":
                # |switch|p1a: Landorus|Landorus-Therian, M, shiny|100/100
                actor_raw = parts[2]   # e.g. "p1a: Landorus"
                pid = actor_raw[:2]    # "p1"
                pokemon = parts[3].split(",")[0].strip()
                battle["actions"].append({
                    "turn": current_turn,
                    "type": "switch",
                    "player": pid,
                    "pokemon": pokemon
                })

            # --- Moves ---
            elif tag == "move":
                # |move|p1a: Landorus|U-turn|p2a: bird1
                actor_raw = parts[2]
                pid = actor_raw[:2]
                move = parts[3]
                target_raw = parts[4] if len(parts) > 4 else ""
                target_pid = target_raw[:2] if target_raw else ""
                battle["actions"].append({
                    "turn": current_turn,
                    "type": "move",
                    "player": pid,
                    "move": move,
                    "target_player": target_pid
                })

            # --- Damage ---
            elif tag == "-damage":
                # |-damage|p2a: bird1|70/100
                target_raw = parts[2]
                pid = target_raw[:2]
                hp = parts[3].split()[0]  # ignore status conditions
                battle["actions"].append({
                    "turn": current_turn,
                    "type": "damage",
                    "player": pid,
                    "hp_remaining": hp
                })

            # --- Winner ---
            elif tag == "win":
                battle["winner"] = parts[2]

    # Derive loser from players
    for pid, name in battle["players"].items():
        if name != battle["winner"]:
            battle["loser"] = name

    return battle


def run_all(log_dir: str = "raw_logs") -> list:
    """Parse all .log files in the directory."""
    results = []
    for log_file in Path(log_dir).glob("*.log"):
        print(f"Parsing {log_file.name}...")
        parsed = parse_log(str(log_file))
        results.append(parsed)
    print(f"Parsed {len(results)} battles.")
    return results


if __name__ == "__main__":
    import json
    battles = run_all()
    # Print the first battle to inspect
    print(json.dumps(battles[0], indent=2))