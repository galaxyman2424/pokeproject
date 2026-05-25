import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from usage_analysis import (
    get_connection,
    pokemon_usage,
    move_usage,
    item_usage,
    tera_usage,
)

OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def export_df(df, name):
    csv_path = OUTPUT_DIR / f"{name}.csv"
    json_path = OUTPUT_DIR / f"{name}.json"
    df.to_csv(csv_path, index=False)
    df.to_json(json_path, orient="records", indent=2)
    print(f"Exported {name} → {csv_path.name}, {json_path.name}")


def main():
    conn = get_connection()

    export_df(pokemon_usage(conn), "pokemon_usage")
    export_df(move_usage(conn), "move_usage")
    export_df(item_usage(conn), "item_usage")

    tera_rate_df, tera_type_df = tera_usage(conn)
    export_df(tera_rate_df, "tera_rate")
    export_df(tera_type_df, "tera_type_distribution")

    # Write a metadata file so later phases know what sample this came from
    meta = {
        "format": "gen9ou",
        "total_battles": int(pokemon_usage(conn)["appearances"].max() / 1),
        "total_teams": 846,  # 423 battles * 2
        "note": "Item data is sparse — only items that activated visibly in battle are recorded. Low observation counts (<10) should not be over-indexed."
    }
    meta_path = OUTPUT_DIR / "meta.json"
    meta_path.write_text(json.dumps(meta, indent=2))
    print(f"Exported metadata → meta.json")

    conn.close()
    print(f"\nAll exports written to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()