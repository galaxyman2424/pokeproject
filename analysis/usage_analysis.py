import sys
from pathlib import Path
import psycopg2
import pandas as pd

sys.path.append(str(Path(__file__).parent.parent))
from config import DB_CONFIG

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

# ── 1. Pokémon Usage % ────────────────────────────────────────────────────────

def pokemon_usage(conn):
    query = """
        SELECT
            p.name,
            COUNT(*)                                      AS appearances,
            COUNT(*) * 100.0 / (SELECT COUNT(*) FROM teams) AS usage_pct,
            SUM(CASE WHEN t.result = 'win' THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN t.result = 'win' THEN 1 ELSE 0 END)
                * 100.0 / COUNT(*)                        AS win_rate
        FROM pokemon p
        JOIN teams t ON p.team_id = t.team_id
        GROUP BY p.name
        ORDER BY appearances DESC
    """
    df = pd.read_sql(query, conn)
    df['usage_pct'] = df['usage_pct'].round(2)
    df['win_rate']  = df['win_rate'].round(2)
    return df

# ── 2. Move Usage % (per Pokémon) ─────────────────────────────────────────────

def move_usage(conn):
    query = """
        SELECT
            p.name                                              AS pokemon,
            m.name                                              AS move,
            COUNT(*)                                            AS times_used,
            COUNT(*) * 100.0 / SUM(COUNT(*)) OVER
                (PARTITION BY p.name)                           AS move_pct
        FROM moves m
        JOIN pokemon p ON m.pokemon_id = p.pokemon_id
        WHERE m.name IS NOT NULL
        GROUP BY p.name, m.name
        ORDER BY p.name, times_used DESC
    """
    df = pd.read_sql(query, conn)
    df['move_pct'] = df['move_pct'].round(2)
    return df

# ── 3. Item Usage % (per Pokémon, observed only) ──────────────────────────────

def item_usage(conn):
    query = """
        SELECT
            p.name                                              AS pokemon,
            p.item,
            COUNT(*)                                            AS times_seen,
            COUNT(*) * 100.0 / SUM(COUNT(*)) OVER
                (PARTITION BY p.name)                           AS item_pct,
            SUM(COUNT(*)) OVER (PARTITION BY p.name)            AS total_observed
        FROM pokemon p
        WHERE p.item IS NOT NULL AND p.item != ''
        GROUP BY p.name, p.item
        ORDER BY p.name, times_seen DESC
    """
    df = pd.read_sql(query, conn)
    df['item_pct'] = df['item_pct'].round(2)
    return df

# ── 4. Tera Usage % (per Pokémon) ─────────────────────────────────────────────

def tera_usage(conn):
    # Tera rate — how often this Pokémon terastallized at all
    tera_rate_query = """
        SELECT
            p.name,
            COUNT(*)                                                AS appearances,
            SUM(CASE WHEN p.tera_type IS NOT NULL THEN 1 ELSE 0 END) AS tera_count,
            SUM(CASE WHEN p.tera_type IS NOT NULL THEN 1 ELSE 0 END)
                * 100.0 / COUNT(*)                                  AS tera_rate
        FROM pokemon p
        GROUP BY p.name
        ORDER BY tera_count DESC
    """

    # Tera type distribution — among tera events, which types?
    tera_type_query = """
        SELECT
            p.name                                              AS pokemon,
            p.tera_type,
            COUNT(*)                                            AS times_used,
            COUNT(*) * 100.0 / SUM(COUNT(*)) OVER
                (PARTITION BY p.name)                           AS type_pct
        FROM pokemon p
        WHERE p.tera_type IS NOT NULL
        GROUP BY p.name, p.tera_type
        ORDER BY p.name, times_used DESC
    """

    tera_rate_df = pd.read_sql(tera_rate_query, conn)
    tera_type_df = pd.read_sql(tera_type_query, conn)

    tera_rate_df['tera_rate'] = tera_rate_df['tera_rate'].round(2)
    tera_type_df['type_pct']  = tera_type_df['type_pct'].round(2)

    return tera_rate_df, tera_type_df

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    conn = get_connection()

    print("\n══════════════════════════════════════════")
    print("  POKÉMON USAGE")
    print("══════════════════════════════════════════")
    usage_df = pokemon_usage(conn)
    print(usage_df.to_string(index=False))

    print("\n══════════════════════════════════════════")
    print("  MOVE USAGE (top 10 Pokémon by appearances)")
    print("══════════════════════════════════════════")
    move_df = move_usage(conn)
    top_pokemon = usage_df.head(10)['name'].tolist()
    print(move_df[move_df['pokemon'].isin(top_pokemon)].to_string(index=False))

    print("\n══════════════════════════════════════════")
    print("  ITEM USAGE (top 10 Pokémon by appearances)")
    print("══════════════════════════════════════════")
    item_df = item_usage(conn)
    print(item_df[item_df['pokemon'].isin(top_pokemon)].to_string(index=False))

    print("\n══════════════════════════════════════════")
    print("  TERA RATE (top 15 by tera count)")
    print("══════════════════════════════════════════")
    tera_rate_df, tera_type_df = tera_usage(conn)
    print(tera_rate_df.head(15).to_string(index=False))

    print("\n══════════════════════════════════════════")
    print("  TERA TYPE DISTRIBUTION (top 10 Pokémon by appearances)")
    print("══════════════════════════════════════════")
    print(tera_type_df[tera_type_df['pokemon'].isin(top_pokemon)].to_string(index=False))

    conn.close()

if __name__ == "__main__":
    main()