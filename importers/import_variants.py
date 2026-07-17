"""Import normalized card variants from the NAS cards-database TypeScript source."""
import re
import sqlite3
import sys
from pathlib import Path
from urllib.parse import unquote

from config import DATA, DATABASE


DISPLAY_NAMES = {
    "normal": "Normal",
    "holo": "Holo",
    "reverse": "Reverse Holo",
    "firstEdition": "1st Edition",
    "shadowless": "Shadowless",
    "unlimited": "Unlimited",
    "promo": "Promo",
}
FINISHES = {"normal", "holo", "reverse"}
EDITIONS = {"firstEdition", "shadowless", "unlimited"}


def normalize(value):
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def ensure_schema(conn):
    columns = {row[1] for row in conn.execute("PRAGMA table_info(variants)")}
    additions = {
        "source_variant_id": "TEXT",
        "name": "TEXT",
        "finish": "TEXT",
        "edition": "TEXT",
    }
    for name, definition in additions.items():
        if name not in columns:
            conn.execute(f"ALTER TABLE variants ADD COLUMN {name} {definition}")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_variants_source_variant_id ON variants(source_variant_id)")


def set_source_map(conn):
    mapping = {}
    for row in conn.execute("SELECT id, github_url FROM sets WHERE github_url IS NOT NULL"):
        source = unquote(row[1]).split("/contents/data/")[-1].split("?ref=")[0]
        mapping[normalize(source)] = row[0]
    return mapping


def parse_variants(text):
    return parse_variant_format(text)[1]


def parse_variant_format(text):
    legacy = re.search(r"variants\s*:\s*\[(.*?)\]", text, re.DOTALL)
    if legacy:
        return "legacy-array", re.findall(r"type\s*:\s*[\"']([^\"']+)", legacy.group(1))
    modern = re.search(r"variants\s*:\s*\{(.*?)\}", text, re.DOTALL)
    if modern:
        return "boolean-object", [key for key, value in re.findall(r"([A-Za-z][A-Za-z0-9_]*)\s*:\s*(true|false)", modern.group(1)) if value == "true"]
    return "none", []


def main():
    if not Path(DATA).is_dir():
        print(f"ERROR: variant source path is missing: {DATA}", file=sys.stderr)
        return 2
    conn = sqlite3.connect(DATABASE)
    try:
        ensure_schema(conn)
        source_sets = set_source_map(conn)
        stats = {"scanned": 0, "cards_with_data": 0, "inserted": 0, "updated": 0, "skipped": 0}
        for path in Path(DATA).rglob("*.ts"):
            relative = path.relative_to(DATA)
            if len(relative.parts) < 3:
                continue
            set_id = source_sets.get(normalize("/".join(relative.parts[:-1])))
            number = path.stem
            if not set_id:
                continue
            card = conn.execute("SELECT id FROM cards WHERE set_id = ? AND number = ?", (set_id, number)).fetchone()
            if not card:
                continue
            stats["scanned"] += 1
            keys = parse_variants(path.read_text(encoding="utf-8"))
            if not keys:
                continue
            stats["cards_with_data"] += 1
            for key in keys:
                source_id = f"{card[0]}:{key}"
                existing = conn.execute("SELECT 1 FROM variants WHERE source_variant_id = ?", (source_id,)).fetchone()
                name = DISPLAY_NAMES.get(key, key)
                conn.execute(
                    "INSERT INTO variants (id, card_id, variant_type, subtype, stamp, size, source_variant_id, name, finish, edition) VALUES (?, ?, ?, NULL, NULL, NULL, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET card_id=excluded.card_id, variant_type=excluded.variant_type, source_variant_id=excluded.source_variant_id, name=excluded.name, finish=excluded.finish, edition=excluded.edition",
                    (source_id, card[0], key, source_id, name, key if key in FINISHES else None, key if key in EDITIONS else None),
                )
                stats["updated" if existing else "inserted"] += 1
        conn.commit()
        stats["skipped"] = conn.execute("SELECT COUNT(*) FROM variants WHERE card_id NOT IN (SELECT id FROM cards)").fetchone()[0]
        print("Cards scanned:", stats["scanned"])
        print("Cards with variant data:", stats["cards_with_data"])
        print("Variant rows inserted:", stats["inserted"])
        print("Variant rows updated:", stats["updated"])
        print("Duplicates/orphans skipped:", stats["skipped"])
        print("Sample rows:")
        for row in conn.execute("SELECT card_id, source_variant_id, name, variant_type, finish, edition FROM variants ORDER BY card_id, id LIMIT 10"):
            print(dict(zip(("card_id", "source_variant_id", "name", "type", "finish", "edition"), row)))
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
