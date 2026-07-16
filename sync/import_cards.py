from database import cursor
from repository import get_series, get_sets, get_cards
from parser import parse_card

import os
from config import DATA

conn, cur = cursor()

total = 0

for series in get_series():

    print(f"\n{series}")

    for set_name in get_sets(series):

        print(f"  {set_name}")

        cards = get_cards(series, set_name)

        # Find this set's database ID
        cur.execute(
            "SELECT id FROM sets WHERE name=?",
            (set_name,)
        )

        row = cur.fetchone()

        if row is None:
            print("    Set not found in database.")
            continue

        set_id = row["id"]

        imported = 0

        for filename in cards:

            number = filename[:-3]

            path = os.path.join(
                DATA,
                series,
                set_name,
                filename
            )

            with open(path, "r", encoding="utf8") as f:
                text = f.read()

            card = parse_card(text)

            if card["name"] is None:
               print()
               print("ERROR")
               print("Series :", series)
               print("Set    :", set_name)
               print("File   :", filename)
               print(path)
               break

            card_id = f"{set_id}_{number}"

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
                category,
                suffix,
                dex_id,
                illustrator,
                evolves_from,
                regulation_mark,
                updated_at
            )
            VALUES
            (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                card_id,
                set_id,
    		number,
    		card["name"],
    		card["rarity"],
   	        card["artist"],
    		card["hp"],
    		card["stage"],
    		card["category"],
    		card["suffix"],
    		card["dex_id"],
    		card["illustrator"],
    		card["evolves_from"],
    		card["regulation_mark"],
    		None
	    ))

            imported += 1
            total += 1

        conn.commit()

        print(f"    Imported {imported}")

print("\n----------------------")
print(f"Imported {total} cards.")
print("----------------------")

conn.close()