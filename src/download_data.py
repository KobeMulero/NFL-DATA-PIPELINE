import ssl
import urllib.request
from pathlib import Path

import certifi
from config import CURRENT_SEASON, SEASONS

ssl_context = ssl.create_default_context(cafile=certifi.where())
opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ssl_context))
urllib.request.install_opener(opener)

BASE_URL = "https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{}.csv.gz"
RAW_DIR = Path("data/raw")
EXTRA_FILES = {
    "players.csv": "https://github.com/nflverse/nflverse-data/releases/download/players/players.csv",
    "teams.csv": "https://github.com/nflverse/nflverse-data/releases/download/teams/teams_colors_logos.csv",
}

def download_season(season):
    url = BASE_URL.format(season)
    dest = RAW_DIR / f"pbp_{season}.csv.gz"
          # Past seasons never change, so only download them once.
      # The current season gets re-downloaded every time to pick up new games.
    if dest.exists() and season != CURRENT_SEASON:
          print(f"Skipping {season} (already downloaded)")
          return
    print(f"Downloading {season} season...")
    urllib.request.urlretrieve(url, dest)
    size_mb = dest.stat().st_size / 1_000_000
    print(f"  Saved {dest} ({size_mb:.1f} MB)")


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for season in SEASONS:
        download_season(season)
    for filename, url in EXTRA_FILES.items():
        print(f"Downloading {filename}...")
        urllib.request.urlretrieve(url, RAW_DIR / filename)


if __name__ == "__main__":
    main()