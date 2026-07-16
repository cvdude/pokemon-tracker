import sqlite3

from config import DATABASE


def count(cur, table):
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    return cur.fetchone()[0]


def scalar(cur, sql):
    cur.execute(sql)
    return cur.fetchone()[0]


def section(title):
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


conn = sqlite3.connect(DATABASE)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

section("EvoDeck Database Verification")

print(f"Series .............. {count(cur, 'series')}")
print(f"Sets ................ {count(cur, 'sets')}")
print(f"Cards ............... {count(cur, 'cards')}")
print(f"Variants ............ {count(cur, 'variants')}")
print(f"Inventory ........... {count(cur, 'inventory')}")

duplicate_cards = scalar(cur, """
SELECT COUNT(*)
FROM (
    SELECT set_id, number
    FROM cards
    GROUP BY set_id, number
    HAVING COUNT(*) > 1
)
""")

missing_images = scalar(cur, """
SELECT COUNT(*)
FROM cards
WHERE image_small IS NULL
   OR image_small=''
""")

missing_logos = scalar(cur, """
SELECT COUNT(*)
FROM sets
WHERE logo IS NULL
   OR logo=''
""")

missing_symbols = scalar(cur, """
SELECT COUNT(*)
FROM sets
WHERE symbol IS NULL
   OR symbol=''
""")

orphan_variants = scalar(cur, """
SELECT COUNT(*)
FROM variants v
LEFT JOIN cards c
ON c.id=v.card_id
WHERE c.id IS NULL
""")

orphan_inventory = scalar(cur, """
SELECT COUNT(*)
FROM inventory i
LEFT JOIN cards c
ON c.id=i.card_id
WHERE c.id IS NULL
""")

section("Health Checks")

print(f"Duplicate Cards ..... {duplicate_cards}")
print(f"Missing Images ...... {missing_images}")
print(f"Missing Logos ....... {missing_logos}")
print(f"Missing Symbols ..... {missing_symbols}")
print(f"Orphan Variants ..... {orphan_variants}")
print(f"Orphan Inventory .... {orphan_inventory}")

section("Missing Logos")

cur.execute("""
SELECT name
FROM sets
WHERE logo IS NULL
   OR logo=''
ORDER BY release_date, name
""")

rows = cur.fetchall()

if rows:
    for row in rows:
        print("-", row["name"])
else:
    print("None")

section("Missing Symbols")

cur.execute("""
SELECT name
FROM sets
WHERE symbol IS NULL
   OR symbol=''
ORDER BY release_date, name
""")

rows = cur.fetchall()

if rows:
    for row in rows:
        print("-", row["name"])
else:
    print("None")

section("Missing Card Images (First 50)")

cur.execute("""
SELECT
    set_id,
    number,
    name
FROM cards
WHERE image_small IS NULL
   OR image_small=''
ORDER BY set_id, number
LIMIT 50
""")

rows = cur.fetchall()

if rows:
    for row in rows:
        print(f"{row['set_id']}  #{row['number']}  {row['name']}")
else:
    print("None")

section("Overall Status")

if (
    duplicate_cards == 0
    and orphan_variants == 0
    and orphan_inventory == 0
):
    print("PASS")
else:
    print("WARNING")

print()
print("=" * 60)

conn.close()