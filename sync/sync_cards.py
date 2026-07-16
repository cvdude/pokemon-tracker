import sqlite3
import requests
import re
import time

DB = "/volume1/web/pokemon-tracker/database/pokemon.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

HEADERS = {
    "User-Agent": "PokemonTracker/1.0"
}

# --------------------------------------------------
# Helper
# --------------------------------------------------

def find(pattern, text):
    m = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    if m:
        return m.group(1).strip()
    return None

# --------------------------------------------------
# Read all sets
# --------------------------------------------------

cur.execute("""
SELECT id, name, github_url
FROM sets
ORDER BY series_id, name
""")

sets = cur.fetchall()

print(f"\nFound {len(sets)} sets.\n")

total_cards = 0

# --------------------------------------------------
# Loop through every set
# --------------------------------------------------

for set_id, set_name, github_url in sets:

    print(f"Reading {set_name}...")

    r = requests.get(github_url, headers=HEADERS)

    if r.status_code != 200:
        print(f"  ERROR {r.status_code}")
        continue

    files = r.json()

    imported = 0

    for item in files:

        if item["type"] != "file":
            continue

        if not item["name"].endswith(".ts"):
            continue

        number = item["name"][:-3]

        raw_url = item["download_url"]

        card = requests.get(raw_url, headers=HEADERS)

        if card.status_code != 200:
            continue

        text = card.text

        # -------------------------
        # Parse card
        # -------------------------

        name = find(r'en:\s*"([^"]+)"', text)
        rarity = find(r'rarity:\s*"([^"]+)"', text)
        artist = find(r'illustrator:\s*"([^"]+)"', text)
        hp = find(r'hp:\s*([0-9]+)', text)
        stage = find(r'stage:\s*"([^"]+)"', text)
        evolves = find(r'evolveFrom:.*?en:\s*"([^"]+)"', text)
        regulation = find(r'regulationMark:\s*"([^"]+)"', text)

        card_id = f"{set_id}-{number}"

        cur.execute("""
        INSERT OR REPLACE INTO cards
        (
            id,
            set_id,
            number,
            name,
            rarity,
            artist,
            hp,
            stage,
            evolves_from,
            regulation_mark
        )
        VALUES (?,?,?,?,?,?,?,?,?,?)
        """,
        (
            card_id,
            set_id,
            number,
            name,
            rarity,
            artist,
            hp,
            stage,
            evolves,
            regulation
        ))

        imported += 1
        total_cards += 1

        # Be nice to GitHub
        time.sleep(0.05)

    conn.commit()

    print(f"  Imported {imported} cards\n")

conn.close()

print("--------------------------------")
print(f"Finished!")
print(f"Imported {total_cards} cards.")
print("--------------------------------")