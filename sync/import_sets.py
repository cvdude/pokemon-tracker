import sqlite3
import requests
import urllib.parse

DB = "/volume1/web/pokemon-tracker/database/pokemon.db"
API = "https://api.github.com/repos/tcgdex/cards-database/contents/data"

db = sqlite3.connect(DB)
cur = db.cursor()

series = cur.execute(
    "SELECT id, name FROM series ORDER BY sort_order"
).fetchall()

set_count = 0

for series_id, series_name in series:

    print(f"\nReading {series_name}...")

    url = API + "/" + urllib.parse.quote(series_name)

    response = requests.get(url)

    if response.status_code != 200:
        print(f"ERROR opening series '{series_name}' ({response.status_code})")
        continue

    folders = response.json()

    for item in folders:

        if item["type"] != "dir":
            continue

        set_name = item["name"]

        print(f"   + {set_name}")

        print(f"      URL: {item['url']}")

        detail_response = requests.get(item["url"])

        print(f"      Status: {detail_response.status_code}")

        if detail_response.status_code != 200:
            print(detail_response.text)
            continue

        try:
            details = detail_response.json()
        except Exception as ex:
            print("JSON ERROR")
            print(ex)
            print(detail_response.text[:500])
            continue

        cur.execute("""
            UPDATE sets
            SET github_url = ?
            WHERE name = ?
              AND series_id = ?
        """, (
            item["url"],
            set_name,
            series_id
        ))

        set_count += 1

db.commit()

print(f"\nUpdated {set_count} sets.")

db.close()