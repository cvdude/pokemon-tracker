import sqlite3

DATABASE = "/volume1/web/pokemon-tracker/database/pokemon.db"

conn = sqlite3.connect(DATABASE)
conn.row_factory = sqlite3.Row
cur = conn.cursor()


def audit_table(table):

    print("\n" + "=" * 60)
    print(table.upper())
    print("=" * 60)

    cur.execute(f"PRAGMA table_info({table})")
    columns = cur.fetchall()

    cur.execute(f"SELECT COUNT(*) FROM {table}")
    total = cur.fetchone()[0]

    print(f"Rows: {total}\n")

    for col in columns:

        name = col["name"]

        cur.execute(f"""
            SELECT COUNT(*)
            FROM {table}
            WHERE {name} IS NULL
               OR TRIM(CAST({name} AS TEXT))=''
        """)

        missing = cur.fetchone()[0]

        percent = round((missing / total) * 100, 1) if total else 0

        print(f"{name:<20} Missing: {missing:<8} ({percent}%)")


for table in [
    "series",
    "sets",
    "cards",
    "locations",
    "inventory"
]:
    audit_table(table)

conn.close()