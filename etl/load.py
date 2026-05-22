import psycopg2
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from config import DB_CONFIG


def load_battle(battle: dict, cursor) -> int:
    """Insert a battle and return its battle_id."""
    cursor.execute("""
    INSERT INTO battles (showdown_id, format, winner, loser)
    VALUES (%s, %s, %s, %s)
    RETURNING battle_id;
    """, (battle["battle_id"], battle["format"], battle["winner"], battle["loser"]))
    return cursor.fetchone()[0]


def load_teams(battle: dict, battle_id: int, cursor):
    """Insert both teams and their pokemon for a battle."""
    players = battle["players"]
    teams = battle["teams"]

    for pid, pokemon_list in teams.items():
        player_name = players.get(pid, "unknown")

        cursor.execute("""
            INSERT INTO teams (battle_id, player, result)
            VALUES (%s, %s, %s)
            RETURNING team_id;
        """, (battle_id, player_name, "win" if player_name == battle["winner"] else "loss"))
        team_id = cursor.fetchone()[0]

        for pokemon_name in pokemon_list:
            cursor.execute("""
                INSERT INTO pokemon (team_id, name)
                VALUES (%s, %s);
            """, (team_id, pokemon_name))


def load_actions(battle: dict, battle_id: int, cursor):
    """Insert all battle actions."""
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
    """Load all parsed battles into PostgreSQL."""
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
        print(f"Connection error: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    from transform import run_all
    battles = run_all()
    load_all(battles)