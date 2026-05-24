import psycopg2
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from config import DB_CONFIG


def load_battle(battle: dict, cursor) -> int:
    cursor.execute("""
    INSERT INTO battles (showdown_id, format, winner)
    VALUES (%s, %s, %s)
    RETURNING battle_id;
    """, (battle["battle_id"], battle["format"], battle["winner_pid"]))
    return cursor.fetchone()[0]


def load_teams(battle: dict, battle_id: int, cursor):
    teams = battle["teams"]
    movesets = battle["movesets"]
    team_hashes = battle["team_hashes"]

    for pid, pokemon_list in teams.items():
        result = "win" if pid == battle["winner_pid"] else "loss"

        cursor.execute("""
            INSERT INTO teams (battle_id, player, result, team_hash)
            VALUES (%s, %s, %s, %s)
            RETURNING team_id;
        """, (battle_id, pid, result, team_hashes[pid]))
        team_id = cursor.fetchone()[0]

        for pokemon_name in pokemon_list:
            moveset = movesets.get(pid, {}).get(pokemon_name, {})
            tera_type = moveset.get("tera_type")
            moves = moveset.get("moves", [])

            cursor.execute("""
                INSERT INTO pokemon (team_id, name, tera_type)
                VALUES (%s, %s, %s)
                RETURNING pokemon_id;
            """, (team_id, pokemon_name, tera_type))
            pokemon_id = cursor.fetchone()[0]

            for slot, move_name in enumerate(moves, start=1):
                cursor.execute("""
                    INSERT INTO moves (pokemon_id, name, move_slot)
                    VALUES (%s, %s, %s);
                """, (pokemon_id, move_name, slot))

        cursor.execute("""
            INSERT INTO team_compositions (team_hash, format, first_seen, times_seen, win_count)
            VALUES (%s, %s, NOW(), 1, 0)
            ON CONFLICT (team_hash) DO UPDATE
                SET times_seen = team_compositions.times_seen + 1;
        """, (team_hashes[pid], battle["format"]))


def load_actions(battle: dict, battle_id: int, cursor):
    for action in battle["actions"]:
        cursor.execute("""
            INSERT INTO battle_actions (battle_id, turn_order, action_type, actor, move_used, target)
            VALUES (%s, %s, %s, %s, %s, %s);
        """, (
            battle_id,
            action.get("turn"),
            action.get("type"),
            action.get("player"),
            action.get("move"),
            action.get("target_player")
        ))


def load_all(battles: list):
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        loaded = 0

        for battle in battles:
            try:
                cursor.execute("SELECT 1 FROM battles WHERE showdown_id = %s", (battle["battle_id"],))
                if cursor.fetchone():
                    print(f"Already exists, skipping: {battle['battle_id']}")
                    continue
                battle_id = load_battle(battle, cursor)
                load_teams(battle, battle_id, cursor)
                load_actions(battle, battle_id, cursor)
                conn.commit()
                loaded += 1
                print(f"Loaded battle {battle['battle_id']}")
            except Exception as e:
                conn.rollback()
                print(f"Skipped {battle['battle_id']}: {e}")

        print(f"\nDone. {loaded}/{len(battles)} battles loaded.")

    except Exception as e:
        conn.rollback()
        print(f"Skipped {battle['battle_id']}: {type(e).__name__}: {e}")


if __name__ == "__main__":
    from transform import run_all
    battles = run_all()
    load_all(battles)