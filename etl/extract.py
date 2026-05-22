import requests
import time
from pathlib import Path

RAW_LOGS_DIR = Path("raw_logs")
RAW_LOGS_DIR.mkdir(exist_ok=True)

def get_replay_ids(format: str = "gen9ou", pages: int = 3) -> list:
    """Fetch a list of replay IDs from Showdown's search API."""
    ids = []
    for page in range(1, pages + 1):
        url = f"https://replay.pokemonshowdown.com/search.json?format={format}&page={page}"
        print(f"Fetching page {page}...")
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Failed on page {page}")
            break
        data = response.json()
        for replay in data:
            ids.append(replay["id"])
        time.sleep(1)  # be polite to the server
    print(f"Found {len(ids)} replays.")
    return ids

def download_replay_log(replay_id: str) -> bool:
    """Download the raw .log file for a given replay ID."""
    url = f"https://replay.pokemonshowdown.com/{replay_id}.log"
    output_path = RAW_LOGS_DIR / f"{replay_id}.log"

    if output_path.exists():
        print(f"Already downloaded: {replay_id}")
        return True

    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to download: {replay_id}")
        return False

    output_path.write_text(response.text, encoding="utf-8")
    print(f"Downloaded: {replay_id}")
    return True

def run(format: str = "gen9ou", pages: int = 3):
    """Main extract function — fetch IDs then download all logs."""
    ids = get_replay_ids(format, pages)
    for replay_id in ids:
        download_replay_log(replay_id)
        time.sleep(0.5)

if __name__ == "__main__":
    run()