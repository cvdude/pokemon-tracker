import requests
import sqlite3

API = "https://api.github.com/repos/tcgdex/cards-database/contents/data"

db = sqlite3.connect("/volume1/web/pokemon-tracker/database/pokemon.db")
cur = db.cursor()

response = requests.get(API)

response.raise_for_status()

items = response.json()

sort_order = 1

for item in items:

    if item["type"] != "dir":
        continue

    name = item["name"]

    print("Adding:", name)

    cur.execute("""
        INSERT OR REPLACE INTO series
        (name, sort_order)
        VALUES (?,?)
    """, (name, sort_order))

    sort_order += 1

db.commit()

print()
print("Imported", sort_order - 1, "series.")

db.close()