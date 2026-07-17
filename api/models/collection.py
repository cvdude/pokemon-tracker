import sqlite3

from config import DATABASE


DEFAULT_USER_ID = 1
DEFAULT_CONDITION = "Near Mint"
DEFAULT_LANGUAGE = "English"
DEFAULT_LOCATION = "Unassigned"


def get_connection():
    conn = sqlite3.connect(str(DATABASE))
    conn.row_factory = sqlite3.Row
    return conn


def create_collection_items(conn):
    conn.execute(
        """
        CREATE TABLE collection_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            card_id TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
            condition TEXT NOT NULL DEFAULT 'Near Mint',
            variant TEXT NOT NULL DEFAULT 'Normal',
            custom_variant TEXT,
            language TEXT NOT NULL DEFAULT 'English',
            ownership_type TEXT NOT NULL DEFAULT 'Raw',
            grading_company TEXT,
            custom_grading_company TEXT,
            grade REAL,
            certification_number TEXT,
            storage_location TEXT NOT NULL DEFAULT 'Unassigned',
            acquisition_date TEXT,
            purchase_price REAL,
            notes TEXT,
            is_favorite INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (card_id) REFERENCES cards(id)
        )
        """
    )


def rebuild_collection_items(conn, columns):
    """Preserve rows while upgrading legacy constrained collection tables."""
    conn.execute("ALTER TABLE collection_items RENAME TO collection_items_legacy")
    create_collection_items(conn)
    language = "language" if "language" in columns else "'English'"
    variant = "CASE WHEN COALESCE(variant, '') = '' THEN 'Normal' ELSE variant END"
    conn.execute(
        f"""
        INSERT INTO collection_items (
            id, user_id, card_id, quantity, condition, variant, language,
            storage_location, acquisition_date, purchase_price, notes, is_favorite,
            created_at, updated_at
        )
        SELECT id, user_id, card_id, quantity, condition, {variant}, {language},
               storage_location, acquisition_date, purchase_price, notes, is_favorite,
               created_at, updated_at
        FROM collection_items_legacy
        """
    )
    conn.execute("DROP TABLE collection_items_legacy")


def ensure_collection_schema():
    """Create independent collection entries without modifying catalog records."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'collection_items'").fetchone()
        if row is None:
            create_collection_items(conn)
        else:
            columns = {item["name"] for item in conn.execute("PRAGMA table_info(collection_items)")}
            if "language" not in columns or "UNIQUE" in (row["sql"] or "").upper():
                rebuild_collection_items(conn, columns)
            columns = {item["name"] for item in conn.execute("PRAGMA table_info(collection_items)")}
            additions = {
                "custom_variant": "TEXT",
                "ownership_type": "TEXT NOT NULL DEFAULT 'Raw'",
                "grading_company": "TEXT",
                "custom_grading_company": "TEXT",
                "grade": "REAL",
                "certification_number": "TEXT",
            }
            for name, definition in additions.items():
                if name not in columns:
                    conn.execute(f"ALTER TABLE collection_items ADD COLUMN {name} {definition}")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_collection_items_card_user ON collection_items (card_id, user_id)")
        conn.execute(
            """
            INSERT INTO collection_items (user_id, card_id, quantity, condition, variant, language, storage_location, notes, is_favorite, created_at, updated_at)
            SELECT i.user_id, i.card_id, i.quantity, 'Near Mint',
                   CASE WHEN COALESCE(i.variant_id, '') = '' THEN 'Normal' ELSE i.variant_id END,
                   'English', COALESCE(l.name, 'Unassigned'), i.notes, i.favorite,
                   COALESCE(i.created_at, CURRENT_TIMESTAMP), COALESCE(i.updated_at, CURRENT_TIMESTAMP)
            FROM inventory i LEFT JOIN locations l ON l.id = i.location_id
            WHERE NOT EXISTS (
                SELECT 1 FROM collection_items ci WHERE ci.user_id = i.user_id AND ci.card_id = i.card_id
            )
            """
        )
        conn.commit()
    finally:
        conn.close()
