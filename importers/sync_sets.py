import sqlite3
import requests

from config import DATABASE, TCGDEX_API, HEADERS

conn = sqlite3.connect(DATABASE)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("Downloading set list...")

response = requests.get(
    f"{TCGDEX_API}/sets",
    headers=HEADERS,
    timeout=30
)
response.raise_for_status()

api_sets = response.json()

print(f"Found {len(api_sets)} sets.\n")

NAME_MAP = {
    "Classic Collection": "Celebrations Classic Collection",
    "McDonald's Collection 2013": "Collection McDonald's 2013",
    "Promos": "Miscellaneous Promos",
}

updated = 0

for api_set in api_sets:

    api_id = api_set["id"]

    print(f"Loading {api_id}...", flush=True)

    response = requests.get(
        f"{TCGDEX_API}/sets/{api_id}",
        headers=HEADERS,
        timeout=30
    )

    if response.status_code != 200:
        print(f"  Failed ({response.status_code})")
        continue

    detail = response.json()

    name = detail.get("name")

    if name in NAME_MAP:
        name = NAME_MAP[name]

    print(f"  Matching: {name}")

    cur.execute("""
        UPDATE sets
        SET
            api_id = ?,
            release_date = ?,
            printed_total = ?,
            total = ?,
            logo = ?,
            symbol = ?
        WHERE name = ?
    """, (
        api_id,
        detail.get("releaseDate"),
        detail.get("cardCount", {}).get("official"),
        detail.get("cardCount", {}).get("total"),
        detail.get("logo"),
        detail.get("symbol"),
        name
    ))

    if cur.rowcount > 0:
        updated += 1

conn.commit()

print("\n-----------------------")
print(f"Updated {updated} sets")
print("-----------------------")

conn.close()