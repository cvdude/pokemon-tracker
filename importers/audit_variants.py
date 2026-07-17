"""Audit explicit TypeScript card variant data against EvoDeck's variants table."""
import argparse
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

from config import DATA, DATABASE
from import_variants import normalize, parse_variants, set_source_map


FIELDS = ("variants", "rarity", "suffix", "category", "edition", "finish", "holo", "reverse", "firstEdition", "shadowless", "promo", "stamp", "legal")


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=str(DATA))
    parser.add_argument("--database", default=str(DATABASE))
    parser.add_argument("--set")
    parser.add_argument("--card")
    parser.add_argument("--limit", type=int, default=10)
    return parser.parse_args()


def main():
    args = arguments()
    source = Path(args.source)
    if not source.is_dir():
        raise SystemExit(f"ERROR: variant source path is missing: {source}")
    conn = sqlite3.connect(args.database)
    try:
        set_map = set_source_map(conn)
        stats, types, sets, series, suspicious, missing = Counter(), Counter(), Counter(), Counter(), [], []
        samples = defaultdict(list)
        for path in source.rglob("*.ts"):
            relative = path.relative_to(source)
            if len(relative.parts) < 3:
                continue
            source_set = normalize("/".join(relative.parts[:-1]))
            set_id = set_map.get(source_set)
            if args.set and args.set not in {set_id, source_set}:
                continue
            if args.card and args.card != path.stem:
                continue
            text = path.read_text(encoding="utf-8")
            stats["files"] += 1
            present = [field for field in FIELDS if re.search(rf"\b{re.escape(field)}\b", text)]
            stats.update(present)
            keys = parse_variants(text)
            if keys:
                stats["cards_with_variants"] += 1
                types.update(keys)
                sets[set_id or source_set] += 1
                era = relative.parts[0]
                if len(samples[era]) < args.limit:
                    samples[era].append(f"{relative}: {', '.join(keys)}")
                if len(keys) > 1:
                    stats["multiple_variants"] += 1
                if set_id:
                    card = conn.execute("SELECT id FROM cards WHERE set_id = ? AND number = ?", (set_id, path.stem)).fetchone()
                    if card:
                        expected = {f"{card[0]}:{key}" for key in keys}
                        actual = {row[0] for row in conn.execute("SELECT source_variant_id FROM variants WHERE card_id = ?", (card[0],))}
                        if not expected.issubset(actual):
                            missing.append((card[0], sorted(expected - actual)))
            elif "variants" in present:
                suspicious.append(str(relative))
            if args.limit and stats["files"] >= args.limit and args.card:
                break
        print("Total card files scanned:", stats["files"])
        print("Cards containing a variants object:", stats["cards_with_variants"])
        print("Recognized source fields:", {field: stats[field] for field in FIELDS})
        print("Counts by variant type:", dict(types))
        print("Counts by set:", dict(sets))
        print("Cards with multiple variants:", stats["multiple_variants"])
        print("Suspicious variant structures:", suspicious[:args.limit])
        print("Source variants missing from SQLite:", missing[:args.limit])
        print("Era samples:")
        for era, rows in samples.items():
            print(era)
            for row in rows:
                print(" ", row)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
