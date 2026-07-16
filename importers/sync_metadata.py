import sqlite3
import requests
import json

from config import DATABASE, TCGDEX_API, HEADERS

conn = sqlite3.connect(DATABASE)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("""
SELECT
    id
FROM cards
ORDER BY id
""")

cards = cur.fetchall()

print(f"Updating {len(cards)} cards...")

updated = 0

for card in cards:

    card_id = card["id"]

    url = f"{TCGDEX_API}/cards/{card_id}"

    r = requests.get(url, headers=HEADERS)

    if r.status_code != 200:
        print(f"Skipping {card_id}")
        continue

    data = r.json()

    image = data.get("image")
    updated_at = data.get("updated")

    cur.execute("""
        UPDATE cards
        SET
            image_small=?,
            updated_at=?
        WHERE id=?
    """, (
        image,
        updated_at,
        card_id
    ))

    updated += 1

    if updated % 250 == 0:
        conn.commit()
        print(updated)

conn.commit()

print()
print(f"Updated {updated} cards.")

conn.close()