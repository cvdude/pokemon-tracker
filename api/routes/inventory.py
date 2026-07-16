from datetime import date
from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request

from config import DATABASE
from models.collection import DEFAULT_CONDITION, DEFAULT_LOCATION, DEFAULT_USER_ID
import sqlite3


inventory = Blueprint("inventory", __name__)


def get_connection():
    conn = sqlite3.connect(str(DATABASE))
    conn.row_factory = sqlite3.Row
    return conn


def get_count(cur, card_id):
    cur.execute(
        """
        SELECT COALESCE(SUM(quantity), 0)
        FROM collection_items
        WHERE user_id = ? AND card_id = ?
        """,
        (DEFAULT_USER_ID, card_id),
    )
    return cur.fetchone()[0]


def request_data():
    return request.get_json(silent=True) or request.form.to_dict()


def parse_quantity(value, default=1):
    if value in (None, ""):
        return default, None
    try:
        quantity = int(value)
    except (TypeError, ValueError):
        return None, "Quantity must be a whole number."
    if not 1 <= quantity <= 1000:
        return None, "Quantity must be between 1 and 1000."
    return quantity, None


def parse_price(value):
    if value in (None, ""):
        return None, None
    try:
        price = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None, "Purchase price must be a valid number."
    if price < 0:
        return None, "Purchase price cannot be negative."
    return float(price), None


def parse_date(value):
    if value in (None, ""):
        return None, None
    try:
        return date.fromisoformat(value).isoformat(), None
    except (TypeError, ValueError):
        return None, "Acquisition date must use YYYY-MM-DD."


def collection_fields(data, include_quantity=True):
    quantity, error = parse_quantity(data.get("quantity")) if include_quantity else (None, None)
    if error:
        return None, error

    price, error = parse_price(data.get("purchase_price"))
    if error:
        return None, error

    acquisition_date, error = parse_date(data.get("acquisition_date"))
    if error:
        return None, error

    fields = {
        "quantity": quantity,
        "condition": (data.get("condition") or DEFAULT_CONDITION).strip()[:100],
        "variant": (data.get("variant") or "").strip()[:100],
        "storage_location": (data.get("storage_location") or DEFAULT_LOCATION).strip()[:100],
        "acquisition_date": acquisition_date,
        "purchase_price": price,
        "notes": (data.get("notes") or "").strip()[:2000] or None,
    }
    if not fields["condition"]:
        fields["condition"] = DEFAULT_CONDITION
    if not fields["storage_location"]:
        fields["storage_location"] = DEFAULT_LOCATION
    return fields, None


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
            INSERT INTO collection_items (
                user_id, card_id, quantity, condition, variant, storage_location,
                acquisition_date, purchase_price, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, card_id, variant, condition, storage_location)
            DO UPDATE SET
                quantity = collection_items.quantity + excluded.quantity,
                acquisition_date = COALESCE(excluded.acquisition_date, collection_items.acquisition_date),
                purchase_price = COALESCE(excluded.purchase_price, collection_items.purchase_price),
                notes = COALESCE(excluded.notes, collection_items.notes),
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                DEFAULT_USER_ID,
                card_id,
                fields["quantity"],
                fields["condition"],
                fields["variant"],
                fields["storage_location"],
                fields["acquisition_date"],
                fields["purchase_price"],
                fields["notes"],
            ),
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
            """
            SELECT id, quantity
            FROM collection_items
            WHERE user_id = ? AND card_id = ?
            ORDER BY updated_at DESC, id DESC
            LIMIT 1
            """,
            (DEFAULT_USER_ID, card_id),
        ).fetchone()
        if row is not None:
            if row["quantity"] > 1:
                cur.execute(
                    "UPDATE collection_items SET quantity = quantity - 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (row["id"],),
                )
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
        item = cur.execute(
            "SELECT card_id FROM collection_items WHERE id = ? AND user_id = ?",
            (item_id, DEFAULT_USER_ID),
        ).fetchone()
        if item is None:
            return jsonify({"success": False, "error": "Collection item not found"}), 404

        assignments = [
            "condition = ?", "variant = ?", "storage_location = ?", "acquisition_date = ?",
            "purchase_price = ?", "notes = ?", "updated_at = CURRENT_TIMESTAMP",
        ]
        values = [
            fields["condition"], fields["variant"], fields["storage_location"],
            fields["acquisition_date"], fields["purchase_price"], fields["notes"],
        ]
        if fields["quantity"] is not None:
            assignments.insert(0, "quantity = ?")
            values.insert(0, fields["quantity"])

        try:
            cur.execute(
                f"UPDATE collection_items SET {', '.join(assignments)} WHERE id = ? AND user_id = ?",
                [*values, item_id, DEFAULT_USER_ID],
            )
        except sqlite3.IntegrityError:
            return jsonify({"success": False, "error": "An identical collection item already exists."}), 409
        conn.commit()
        count = get_count(cur, item["card_id"])
    finally:
        conn.close()

    return jsonify({"success": True, "count": count})
