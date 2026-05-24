from pathlib import Path
from typing import Dict
import hashlib

def generate_team_hash(names: list) -> str:
    canonical = sorted([n.lower().strip() for n in names])
    return hashlib.md5(",".join(canonical).encode()).hexdigest()

def parse_log(file_path: str) -> Dict:
    """Parse a raw Showdown .log file into a structured dictionary."""
    
    battle = {
        "battle_id": Path(file_path).stem,
        "format": None,
        "winner": None,
        "loser": None,
        "players": {},
        "teams": {"p1": [], "p2": []},
        "movesets": {"p1": {}, "p2": {}},  # add this
        "actions": []
    }
    active_pokemon = {"p1": None, "p2": None}

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
                pid = parts[2]
                name = parts[3] if len(parts) > 3 else ""
                if name:  # only store if name is not empty
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
                actor_raw = parts[2]
                pid = actor_raw[:2]
                pokemon = parts[3].split(",")[0].strip()
                active_pokemon[pid] = pokemon  # track who is active
                battle["actions"].append({
                    "turn": current_turn,
                    "type": "switch",
                    "player": pid,
                    "pokemon": pokemon
                })

            # --- Moves ---
            elif tag == "move":
                actor_raw = parts[2]
                pid = actor_raw[:2]
                move = parts[3]
                target_raw = parts[4] if len(parts) > 4 else ""
                target_pid = target_raw[:2] if target_raw else ""
                
                pokemon = active_pokemon[pid]
                
                if pokemon:
                    if pokemon not in battle["movesets"][pid]:
                        battle["movesets"][pid][pokemon] = {"moves": [], "tera_type": None}
                    if move not in battle["movesets"][pid][pokemon]["moves"]:
                        battle["movesets"][pid][pokemon]["moves"].append(move)
                
                battle["actions"].append({
                    "turn": current_turn,
                    "type": "move",
                    "player": pid,
                    "pokemon": pokemon,
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
            
            elif tag == "-terastallize":
                pid = parts[2][:2]
                tera_type = parts[3]
                pokemon = active_pokemon[pid]
                if pokemon and pid in battle["movesets"]:
                    if pokemon not in battle["movesets"][pid]:
                        battle["movesets"][pid][pokemon] = {"moves": [], "tera_type": None}
                    battle["movesets"][pid][pokemon]["tera_type"] = tera_type
                battle["actions"].append({
                    "turn": current_turn,
                    "type": "terastallize",
                    "player": pid,
                    "tera_type": tera_type
                })

            # --- Winner ---
            elif tag == "win":
                battle["winner"] = parts[2]

    # Derive loser from players
    for pid, name in battle["players"].items():
        if name != battle["winner"]:
            battle["loser"] = name

    # Generate team hashes
    battle["team_hashes"] = {
        "p1": generate_team_hash(battle["teams"]["p1"]),
        "p2": generate_team_hash(battle["teams"]["p2"])
    }

    # Resolve which pid won
    for pid, name in battle["players"].items():
        if name == battle["winner"]:
            battle["winner_pid"] = pid
            break
    else:
        print(f"NO MATCH — players: {battle['players']}, winner: '{battle['winner']}'")

    # Remove names from output
    del battle["players"]
    del battle["winner"]
    del battle["loser"]
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