import sqlite3
import requests

from config import DATABASE, TCGDEX_API, HEADERS
from mapping import map_set_id

conn = sqlite3.connect(DATABASE)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=" * 60)
print(" EvoDeck Card Synchronizer")
print("=" * 60)
print()

cur.execute("""
SELECT
    id,
    api_id,
    name
FROM sets
WHERE api_id IS NOT NULL
ORDER BY name
""")

sets = cur.fetchall()

print(f"Found {len(sets)} sets.\n")

updated = 0
missing = 0

missing_cards = []

for s in sets:

    print(f"Reading {s['name']}")

    try:

        response = requests.get(
            f"{TCGDEX_API}/sets/{s['api_id']}",
            headers=HEADERS,
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

    except Exception as ex:

        print(f"  ERROR: {ex}")
        continue

    cards = data.get("cards", [])

    print(f"  {len(cards)} cards")

    for card in cards:

        api_card_id = card.get("id")
        local_number = card.get("localId")
        card_name = card.get("name")
        image = card.get("image")

        target_set_id = map_set_id(
            s["id"],
            local_number
        )

        #
        # First try matching by number
        #

        cur.execute("""
        UPDATE cards
        SET
            api_card_id = ?,
            image_small = ?
        WHERE
            set_id = ?
        AND
            number = ?
        """,
        (
            api_card_id,
            image,
            target_set_id,
            local_number
        ))

        #
        # If that didn't work, try matching by name
        #

        if cur.rowcount == 0:

            cur.execute("""
            UPDATE cards
            SET
                api_card_id = ?,
                image_small = ?
            WHERE
                set_id = ?
            AND
                name = ?
            """,
            (
                api_card_id,
                image,
                target_set_id,
                card_name
            ))

        if cur.rowcount:

            updated += 1

        else:

            missing += 1

            if len(missing_cards) < 100:

                missing_cards.append(
                    (
                        s["name"],
                        local_number,
                        card_name,
                        api_card_id
                    )
                )

    conn.commit()

print()
print("=" * 60)
print(f"Cards Updated : {updated}")
print(f"Cards Missing : {missing}")

if missing_cards:

    print()
    print("First Missing Cards")
    print("-" * 60)

    for set_name, number, name, api_id in missing_cards:

        print(
            f"{set_name:35} "
            f"{str(number):8} "
            f"{name:30} "
            f"{api_id}"
        )

print("=" * 60)

conn.close()