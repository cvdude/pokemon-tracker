from datetime import date
from decimal import Decimal, InvalidOperation
import sqlite3

from flask import Blueprint, jsonify, request

from config import DATABASE
from models.collection import DEFAULT_CONDITION, DEFAULT_LANGUAGE, DEFAULT_LOCATION, DEFAULT_USER_ID


inventory = Blueprint("inventory", __name__)

CONDITIONS = {"Mint", "Near Mint", "Lightly Played", "Moderately Played", "Heavily Played", "Damaged"}
VARIANTS = {"Normal", "Holo", "Reverse Holo", "1st Edition", "Shadowless", "Promo"}
LANGUAGES = {"English", "Japanese"}


def get_connection():
    conn = sqlite3.connect(str(DATABASE))
    conn.row_factory = sqlite3.Row
    return conn


def get_count(cur, card_id):
    return cur.execute(
        "SELECT COALESCE(SUM(quantity), 0) FROM collection_items WHERE user_id = ? AND card_id = ?",
        (DEFAULT_USER_ID, card_id),
    ).fetchone()[0]


def request_data():
    return request.get_json(silent=True) or request.form.to_dict()


def parse_quantity(value, default=1):
    if value in (None, ""):
        return default, None
    try:
        quantity = int(value)
    except (TypeError, ValueError):
        return None, "Quantity must be a whole number."
    return (quantity, None) if 1 <= quantity <= 1000 else (None, "Quantity must be between 1 and 1000.")


def parse_price(value):
    if value in (None, ""):
        return None, None
    try:
        value = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None, "Purchase price must be a valid number."
    return (float(value), None) if value >= 0 else (None, "Purchase price cannot be negative.")


def parse_date(value):
    if value in (None, ""):
        return date.today().isoformat(), None
    try:
        return date.fromisoformat(value).isoformat(), None
    except (TypeError, ValueError):
        return None, "Date acquired must use YYYY-MM-DD."


def selected_value(data, field, allowed, default):
    value = (data.get(field) or default).strip()
    if value != "Other":
        return (value, None) if value in allowed else (None, f"Invalid {field}.")
    other = (data.get(f"{field}_other") or "").strip()[:100]
    return (f"Other: {other}", None) if other else (None, f"Specify the other {field}.")


def collection_fields(data, include_quantity=True):
    quantity, error = parse_quantity(data.get("quantity")) if include_quantity else (None, None)
    if error:
        return None, error
    price, error = parse_price(data.get("purchase_price"))
    if error:
        return None, error
    acquired, error = parse_date(data.get("acquisition_date"))
    if error:
        return None, error
    condition = (data.get("condition") or DEFAULT_CONDITION).strip()
    if condition not in CONDITIONS:
        return None, "Invalid condition."
    variant, error = selected_value(data, "variant", VARIANTS, "Normal")
    if error:
        return None, error
    language, error = selected_value(data, "language", LANGUAGES, DEFAULT_LANGUAGE)
    if error:
        return None, error
    location = (data.get("storage_location") or DEFAULT_LOCATION).strip()[:100]
    if not location:
        return None, "Storage location is required."
    return {
        "quantity": quantity, "condition": condition, "variant": variant, "language": language,
        "storage_location": location, "acquisition_date": acquired, "purchase_price": price,
        "notes": (data.get("notes") or "").strip()[:2000] or None,
    }, None


def card_exists(cur, card_id):
    return cur.execute("SELECT 1 FROM cards WHERE id = ?", (card_id,)).fetchone() is not None


@inventory.route("/inventory/count/<card_id>")
def inventory_count(card_id):
    conn = get_connection()
    try:
        count = get_count(conn.cursor(), card_id)
    finally:
        conn.close()
    return jsonify({"count": count})


@inventory.route("/collection/items/card/<card_id>")
def collection_items_for_card(card_id):
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM collection_items WHERE user_id = ? AND card_id = ? ORDER BY updated_at DESC, id DESC",
            (DEFAULT_USER_ID, card_id),
        ).fetchall()
    finally:
        conn.close()
    return jsonify({"items": [dict(row) for row in rows]})


@inventory.route("/inventory/add/<card_id>", methods=["POST"])
@inventory.route("/collection/items/<card_id>", methods=["POST"])
def add_card(card_id):
    fields, error = collection_fields(request_data())
    if error:
        return jsonify({"success": False, "error": error}), 400
    conn = get_connection()
    try:
        cur = conn.cursor()
        if not card_exists(cur, card_id):
            return jsonify({"success": False, "error": "Card not found"}), 404
        cur.execute(
            """
            INSERT INTO collection_items (user_id, card_id, quantity, condition, variant, language, storage_location, acquisition_date, purchase_price, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, card_id, variant, condition, language, storage_location) DO UPDATE SET
                quantity = collection_items.quantity + excluded.quantity,
                acquisition_date = excluded.acquisition_date, purchase_price = COALESCE(excluded.purchase_price, collection_items.purchase_price),
                notes = COALESCE(excluded.notes, collection_items.notes), updated_at = CURRENT_TIMESTAMP
            """,
            (DEFAULT_USER_ID, card_id, fields["quantity"], fields["condition"], fields["variant"], fields["language"], fields["storage_location"], fields["acquisition_date"], fields["purchase_price"], fields["notes"]),
        )
        conn.commit()
        count = get_count(cur, card_id)
    finally:
        conn.close()
    return jsonify({"success": True, "count": count})


@inventory.route("/inventory/remove/<card_id>", methods=["POST"])
def remove_card(card_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        row = cur.execute(
            "SELECT id, quantity FROM collection_items WHERE user_id = ? AND card_id = ? ORDER BY updated_at DESC, id DESC LIMIT 1",
            (DEFAULT_USER_ID, card_id),
        ).fetchone()
        if row:
            if row["quantity"] > 1:
                cur.execute("UPDATE collection_items SET quantity = quantity - 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (row["id"],))
            else:
                cur.execute("DELETE FROM collection_items WHERE id = ?", (row["id"],))
            conn.commit()
        count = get_count(cur, card_id)
    finally:
        conn.close()
    return jsonify({"success": True, "count": count})


@inventory.route("/collection/items/<int:item_id>", methods=["PATCH"])
def update_collection_item(item_id):
    data = request_data()
    fields, error = collection_fields(data, include_quantity="quantity" in data)
    if error:
        return jsonify({"success": False, "error": error}), 400
    conn = get_connection()
    try:
        cur = conn.cursor()
        item = cur.execute("SELECT card_id FROM collection_items WHERE id = ? AND user_id = ?", (item_id, DEFAULT_USER_ID)).fetchone()
        if item is None:
            return jsonify({"success": False, "error": "Collection item not found"}), 404
        assignments = ["condition = ?", "variant = ?", "language = ?", "storage_location = ?", "acquisition_date = ?", "purchase_price = ?", "notes = ?", "updated_at = CURRENT_TIMESTAMP"]
        values = [fields["condition"], fields["variant"], fields["language"], fields["storage_location"], fields["acquisition_date"], fields["purchase_price"], fields["notes"]]
        if fields["quantity"] is not None:
            assignments.insert(0, "quantity = ?")
            values.insert(0, fields["quantity"])
        try:
            cur.execute(f"UPDATE collection_items SET {', '.join(assignments)} WHERE id = ? AND user_id = ?", [*values, item_id, DEFAULT_USER_ID])
        except sqlite3.IntegrityError:
            return jsonify({"success": False, "error": "An identical collection item already exists."}), 409
        conn.commit()
        count = get_count(cur, item["card_id"])
    finally:
        conn.close()
    return jsonify({"success": True, "count": count})
