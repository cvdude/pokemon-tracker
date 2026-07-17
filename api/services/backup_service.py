"""Forward-compatible collection export, import, and SQLite backup helpers."""

import csv
import io
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from config import DATABASE
from models.collection import DEFAULT_USER_ID, ensure_collection_schema


BACKUP_DIR = Path(DATABASE).parent.parent / "backups"
FORMAT_VERSION = 1
COLLECTION_TABLES = ("collection_items", "wishlist_items")


def _connection():
    conn = sqlite3.connect(str(DATABASE))
    conn.row_factory = sqlite3.Row
    return conn


def _timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def _rows(conn, table, where="", params=()):
    return [dict(row) for row in conn.execute(f"SELECT * FROM {table} {where}", params).fetchall()]


def export_payload(export_type):
    """Return a versioned JSON envelope containing only user-owned data."""
    if export_type not in {"collection", "inventory", "wishlist", "trade", "purchases", "values"}:
        raise ValueError("Unsupported export type.")
    conn = _connection()
    try:
        collection_where = "WHERE user_id = ?"
        params = (DEFAULT_USER_ID,)
        if export_type == "trade":
            collection_where += " AND is_trade = 1"
        elif export_type == "purchases":
            collection_where += " AND (purchase_price IS NOT NULL OR purchase_date IS NOT NULL OR purchase_source IS NOT NULL)"
        elif export_type == "values":
            collection_where += " AND (estimated_value IS NOT NULL OR insurance_value IS NOT NULL)"
        data = {}
        if export_type != "wishlist":
            data["collection_items"] = _rows(conn, "collection_items", collection_where, params)
        if export_type in {"collection", "wishlist"}:
            data["wishlist_items"] = _rows(conn, "wishlist_items", "WHERE user_id = ?", params)
    finally:
        conn.close()
    return {
        "format": "evodeck-collection-export",
        "format_version": FORMAT_VERSION,
        "export_type": export_type,
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "data": data,
    }


def csv_rows(payload):
    """Flatten one export into spreadsheet-friendly row dictionaries."""
    rows = []
    for table, records in payload["data"].items():
        for record in records:
            rows.append({"record_type": table, **record})
    return rows


def parse_import(raw_bytes, filename=""):
    """Parse a versioned JSON export or a collection-items CSV file."""
    text = raw_bytes.decode("utf-8-sig")
    if filename.lower().endswith(".csv"):
        records = list(csv.DictReader(io.StringIO(text)))
        collection_items, wishlist_items = [], []
        for record in records:
            record_type = record.pop("record_type", "collection_items") or "collection_items"
            target = wishlist_items if record_type == "wishlist_items" else collection_items
            target.append({key: value if value != "" else None for key, value in record.items()})
        return {"format_version": FORMAT_VERSION, "data": {"collection_items": collection_items, "wishlist_items": wishlist_items}}
    payload = json.loads(text)
    if payload.get("format") != "evodeck-collection-export":
        raise ValueError("This is not an EvoDeck collection export.")
    version = payload.get("format_version")
    if not isinstance(version, int) or version > FORMAT_VERSION:
        raise ValueError("This export uses a newer unsupported format version.")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise ValueError("The export data section is invalid.")
    for table in COLLECTION_TABLES:
        if table in data and not isinstance(data[table], list):
            raise ValueError(f"The {table} section is invalid.")
    return {"format_version": version, "data": {table: data.get(table, []) for table in COLLECTION_TABLES}}


def _identity(record, table):
    if table == "wishlist_items":
        return (record.get("card_id"), record.get("source_variant_id") or "")
    return (
        record.get("card_id"), record.get("source_variant_id") or "", record.get("variant") or "Normal",
        record.get("condition") or "", record.get("language") or "English", record.get("storage_location") or "Unassigned",
        record.get("ownership_type") or "Raw", str(record.get("grade") or ""), record.get("certification_number") or "",
    )


def preview_import(payload):
    """Summarize import rows and duplicates without changing the database."""
    data = payload["data"]
    conn = _connection()
    try:
        existing = {table: {_identity(row, table) for row in _rows(conn, table, "WHERE user_id = ?", (DEFAULT_USER_ID,))} for table in COLLECTION_TABLES}
    finally:
        conn.close()
    summary = {}
    for table in COLLECTION_TABLES:
        records = data.get(table, [])
        duplicates = sum(1 for record in records if _identity(record, table) in existing[table])
        summary[table] = {"rows": len(records), "duplicates": duplicates, "new_rows": len(records) - duplicates}
    return summary


def create_database_backup(operation, notes=None):
    """Create a consistent SQLite snapshot and record it in backup history."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"pokemon_{_timestamp()}_{operation}.db"
    target = BACKUP_DIR / filename
    source = sqlite3.connect(str(DATABASE))
    destination = sqlite3.connect(str(target))
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()
    conn = _connection()
    try:
        conn.execute("INSERT INTO backup_history (filename, operation, file_size, notes) VALUES (?, ?, ?, ?)", (filename, operation, target.stat().st_size, notes))
        conn.commit()
    finally:
        conn.close()
    return {"filename": filename, "file_size": target.stat().st_size}


def _valid_card_ids(conn, records):
    ids = {record.get("card_id") for record in records if record.get("card_id")}
    valid = set()
    for chunk in (list(ids)[index:index + 500] for index in range(0, len(ids), 500)):
        placeholders = ",".join("?" for _ in chunk)
        valid.update(row[0] for row in conn.execute(f"SELECT id FROM cards WHERE id IN ({placeholders})", chunk))
    return valid


def apply_import(payload, mode):
    """Apply a merge or replacement import in one transaction after a snapshot."""
    if mode not in {"merge", "replace"}:
        raise ValueError("Import mode must be merge or replace.")
    data = payload["data"]
    for record in data["collection_items"] + data["wishlist_items"]:
        if not isinstance(record, dict) or not record.get("card_id"):
            raise ValueError("Every imported record must include a card ID.")
    for record in data["collection_items"]:
        try:
            if int(record.get("quantity") or 1) < 1:
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError("Collection item quantity must be a positive whole number.") from None
    records = data["collection_items"] + data["wishlist_items"]
    backup = create_database_backup("before-import", f"{mode} import")
    conn = _connection()
    conn.row_factory = sqlite3.Row
    try:
        valid_cards = _valid_card_ids(conn, records)
        missing = sorted({record.get("card_id") for record in records if record.get("card_id") not in valid_cards})
        if missing:
            raise ValueError(f"Import references {len(missing)} card(s) not in this catalog.")
        conn.execute("BEGIN")
        if mode == "replace":
            conn.execute("DELETE FROM collection_items WHERE user_id = ?", (DEFAULT_USER_ID,))
            conn.execute("DELETE FROM wishlist_items WHERE user_id = ?", (DEFAULT_USER_ID,))
        result = {"inserted": 0, "merged": 0}
        for table in COLLECTION_TABLES:
            existing = {_identity(row, table): dict(row) for row in _rows(conn, table, "WHERE user_id = ?", (DEFAULT_USER_ID,))}
            columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
            protected = {"id", "user_id"}
            for incoming in data[table]:
                key = _identity(incoming, table)
                if key in existing and mode == "merge":
                    if table == "collection_items":
                        conn.execute("UPDATE collection_items SET quantity = quantity + ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (int(incoming.get("quantity") or 1), existing[key]["id"]))
                    else:
                        conn.execute("UPDATE wishlist_items SET priority = ?, desired_condition = ?, target_price = ?, notes = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (incoming.get("priority") or "Medium", incoming.get("desired_condition"), incoming.get("target_price"), incoming.get("notes"), existing[key]["id"]))
                    result["merged"] += 1
                    continue
                values = {name: value for name, value in incoming.items() if name in columns and name not in protected}
                values["user_id"] = DEFAULT_USER_ID
                if table == "collection_items":
                    values.setdefault("quantity", 1)
                    values.setdefault("condition", "Near Mint")
                    values.setdefault("variant", "Normal")
                    values.setdefault("language", "English")
                    values.setdefault("storage_location", "Unassigned")
                    values.setdefault("ownership_type", "Raw")
                    values.setdefault("currency", "USD")
                    values.setdefault("is_trade", 0)
                else:
                    values.setdefault("priority", "Medium")
                names = list(values)
                conn.execute(f"INSERT INTO {table} ({', '.join(names)}) VALUES ({', '.join('?' for _ in names)})", [values[name] for name in names])
                result["inserted"] += 1
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return {**result, "backup": backup}


def backup_history():
    conn = _connection()
    try:
        rows = _rows(conn, "backup_history", "ORDER BY created_at DESC, id DESC")
    finally:
        conn.close()
    return [row for row in rows if (BACKUP_DIR / row["filename"]).is_file()]


def restore_backup(backup_id):
    history = {row["id"]: row for row in backup_history()}
    if backup_id not in history:
        raise ValueError("Backup not found.")
    source_path = BACKUP_DIR / history[backup_id]["filename"]
    before = create_database_backup("before-restore", f"restore {history[backup_id]['filename']}")
    preserved_history = backup_history()
    source = sqlite3.connect(str(source_path))
    destination = sqlite3.connect(str(DATABASE))
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()
    ensure_collection_schema()
    conn = _connection()
    try:
        for item in preserved_history:
            conn.execute(
                """INSERT OR IGNORE INTO backup_history
                   (filename, operation, created_at, file_size, notes) VALUES (?, ?, ?, ?, ?)""",
                (item["filename"], item["operation"], item["created_at"], item["file_size"], item["notes"]),
            )
        conn.commit()
    finally:
        conn.close()
    after = create_database_backup("after-restore", f"restored {history[backup_id]['filename']}")
    return {"before": before, "after": after}
