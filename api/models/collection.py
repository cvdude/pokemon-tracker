import sqlite3

from config import DATABASE


DEFAULT_USER_ID = 1
DEFAULT_CONDITION = "Unspecified"
DEFAULT_LOCATION = "Unassigned"


def get_connection():
    conn = sqlite3.connect(str(DATABASE))
    conn.row_factory = sqlite3.Row
    return conn


def ensure_collection_schema():
    """Create the ownership table and migrate the legacy inventory once."""
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS collection_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                card_id TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
                condition TEXT NOT NULL DEFAULT 'Unspecified',
                variant TEXT NOT NULL DEFAULT '',
                storage_location TEXT NOT NULL DEFAULT 'Unassigned',
                acquisition_date TEXT,
                purchase_price REAL,
                notes TEXT,
                is_favorite INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (card_id) REFERENCES cards(id),
                UNIQUE (user_id, card_id, variant, condition, storage_location)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_collection_items_card_user
            ON collection_items (card_id, user_id)
            """
        )

        conn.execute(
            """
            INSERT OR IGNORE INTO collection_items (
                user_id, card_id, quantity, condition, variant, storage_location,
                notes, is_favorite, created_at, updated_at
            )
            SELECT
                i.user_id,
                i.card_id,
                i.quantity,
                'Unspecified',
                COALESCE(i.variant_id, ''),
                COALESCE(l.name, 'Unassigned'),
                i.notes,
                i.favorite,
                COALESCE(i.created_at, CURRENT_TIMESTAMP),
                COALESCE(i.updated_at, CURRENT_TIMESTAMP)
            FROM inventory i
            LEFT JOIN locations l ON l.id = i.location_id
            """
        )
        conn.commit()
    finally:
        conn.close()
