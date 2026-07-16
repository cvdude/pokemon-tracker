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


def create_collection_items(conn, table_name="collection_items"):
    conn.execute(
        f"""
        CREATE TABLE {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            card_id TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
            condition TEXT NOT NULL DEFAULT 'Near Mint',
            variant TEXT NOT NULL DEFAULT 'Normal',
            language TEXT NOT NULL DEFAULT 'English',
            storage_location TEXT NOT NULL DEFAULT 'Unassigned',
            acquisition_date TEXT,
            purchase_price REAL,
            notes TEXT,
            is_favorite INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (card_id) REFERENCES cards(id),
            UNIQUE (user_id, card_id, variant, condition, language, storage_location)
        )
        """
    )


def rebuild_collection_items_for_language(conn):
    """Upgrade the original collection key so language distinguishes copies."""
    conn.execute("ALTER TABLE collection_items RENAME TO collection_items_legacy")
    create_collection_items(conn)
    conn.execute(
        """
        INSERT INTO collection_items (
            id, user_id, card_id, quantity, condition, variant, language,
            storage_location, acquisition_date, purchase_price, notes, is_favorite,
            created_at, updated_at
        )
        SELECT
            id, user_id, card_id, quantity, condition,
            CASE WHEN variant = '' THEN 'Normal' ELSE variant END,
            'English', storage_location, acquisition_date, purchase_price, notes,
            is_favorite, created_at, updated_at
        FROM collection_items_legacy
        """
    )
    conn.execute("DROP TABLE collection_items_legacy")


def ensure_collection_schema():
    """Create or migrate collection ownership without changing catalog records."""
    conn = get_connection()
    try:
        table_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'collection_items'"
        ).fetchone()
        if not table_exists:
            create_collection_items(conn)
        else:
            table_sql = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'collection_items'"
            ).fetchone()[0] or ""
            if "language" not in table_sql.lower() or "variant, condition, language, storage_location" not in table_sql.lower():
                rebuild_collection_items_for_language(conn)

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_collection_items_card_user ON collection_items (card_id, user_id)"
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO collection_items (
                user_id, card_id, quantity, condition, variant, language,
                storage_location, notes, is_favorite, created_at, updated_at
            )
            SELECT i.user_id, i.card_id, i.quantity, 'Near Mint',
                   CASE WHEN COALESCE(i.variant_id, '') = '' THEN 'Normal' ELSE i.variant_id END,
                   'English', COALESCE(l.name, 'Unassigned'), i.notes, i.favorite,
                   COALESCE(i.created_at, CURRENT_TIMESTAMP), COALESCE(i.updated_at, CURRENT_TIMESTAMP)
            FROM inventory i
            LEFT JOIN locations l ON l.id = i.location_id
            """
        )
        conn.commit()
    finally:
        conn.close()
