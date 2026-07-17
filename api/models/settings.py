"""Extensible per-user preference storage and validation."""

import json

from config import DATABASE
from models.collection import DEFAULT_USER_ID, get_connection


DEFAULT_SETTINGS = {
    "default_collection_view": "collection",
    "theme": "system",
    "card_image_size": "medium",
    "default_sort": "name",
    "default_order": "asc",
    "default_filters": {"ownership": "owned"},
    "currency": "USD",
    "date_format": "YYYY-MM-DD",
    "dashboard_widgets": [
        "progress", "summary", "valuation", "analytics", "wishlist_trade", "top_sets", "recent_duplicates",
    ],
    "hidden_dashboard_widgets": [],
}

CHOICES = {
    "default_collection_view": {"catalog", "collection", "dashboard"},
    "theme": {"light", "dark", "system"},
    "card_image_size": {"small", "medium", "large"},
    "default_sort": {"name", "set", "number", "rarity", "quantity", "updated"},
    "default_order": {"asc", "desc"},
    "currency": {"USD", "CAD", "EUR", "GBP", "JPY", "AUD"},
    "date_format": {"YYYY-MM-DD", "MM/DD/YYYY", "DD/MM/YYYY"},
}
FILTER_KEYS = {"ownership", "duplicates", "grading", "master", "has_notes", "wishlist", "trade", "never_valued", "value_changed", "purchased_month", "purchased_year"}
WIDGETS = set(DEFAULT_SETTINGS["dashboard_widgets"])


def ensure_settings_schema():
    conn = get_connection()
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER NOT NULL,
                setting_key TEXT NOT NULL,
                setting_value TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, setting_key),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )"""
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_user_settings_user ON user_settings (user_id, setting_key)")
        conn.commit()
    finally:
        conn.close()


def _decode(key, value):
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return DEFAULT_SETTINGS.get(key)


def get_settings(user_id=DEFAULT_USER_ID):
    """Return defaults merged with the current user's stored JSON values."""
    settings = {key: value.copy() if isinstance(value, dict) else list(value) if isinstance(value, list) else value for key, value in DEFAULT_SETTINGS.items()}
    conn = get_connection()
    try:
        rows = conn.execute("SELECT setting_key, setting_value FROM user_settings WHERE user_id = ?", (user_id,)).fetchall()
    finally:
        conn.close()
    for row in rows:
        if row["setting_key"] in settings:
            settings[row["setting_key"]] = _decode(row["setting_key"], row["setting_value"])
    return settings


def validate_settings(values):
    """Return a normalized, safe partial settings update."""
    if not isinstance(values, dict):
        raise ValueError("Settings must be an object.")
    normalized = {}
    for key, value in values.items():
        if key in CHOICES:
            if value not in CHOICES[key]:
                raise ValueError(f"Invalid {key.replace('_', ' ')}.")
            normalized[key] = value
        elif key == "default_filters":
            if not isinstance(value, dict):
                raise ValueError("Default filters must be an object.")
            filters = {name: filter_value for name, filter_value in value.items() if name in FILTER_KEYS and filter_value not in {"", False, None}}
            if filters.get("ownership") not in {None, "owned", "missing", "all"}:
                raise ValueError("Invalid default ownership filter.")
            normalized[key] = filters
        elif key in {"dashboard_widgets", "hidden_dashboard_widgets"}:
            if not isinstance(value, list) or any(item not in WIDGETS for item in value) or len(set(value)) != len(value):
                raise ValueError("Invalid dashboard widget list.")
            normalized[key] = value
    return normalized


def save_settings(values, user_id=DEFAULT_USER_ID):
    normalized = validate_settings(values)
    if not normalized:
        return get_settings(user_id)
    conn = get_connection()
    try:
        for key, value in normalized.items():
            conn.execute(
                """INSERT INTO user_settings (user_id, setting_key, setting_value, updated_at)
                   VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(user_id, setting_key) DO UPDATE SET setting_value = excluded.setting_value, updated_at = CURRENT_TIMESTAMP""",
                (user_id, key, json.dumps(value, separators=(",", ":"))),
            )
        conn.commit()
    finally:
        conn.close()
    return get_settings(user_id)
