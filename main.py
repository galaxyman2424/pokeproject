from etl.extract import run as extract
from etl.transform import run_all as transform
from etl.load import load_all as load

if __name__ == "__main__":
    print("=== Step 1: Extracting replays ===")
    extract(format="gen9ou", pages=3)

    print("\n=== Step 2: Transforming logs ===")
    battles = transform()

    print("\n=== Step 3: Loading into PostgreSQL ===")
    load(battles)

    print("\n=== Pipeline complete ===")