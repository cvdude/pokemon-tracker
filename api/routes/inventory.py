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
GRADING_COMPANIES = {"PSA", "CGC", "Beckett/BGS", "SGC", "TAG", "ACE"}
WISHLIST_PRIORITIES = {"Low", "Medium", "High"}


def get_connection():
    conn = sqlite3.connect(str(DATABASE))
    conn.row_factory = sqlite3.Row
    return conn


def get_count(cur, card_id):
    return cur.execute("SELECT COALESCE(SUM(quantity), 0) FROM collection_items WHERE user_id = ? AND card_id = ?", (DEFAULT_USER_ID, card_id)).fetchone()[0]


def request_data():
    return request.get_json(silent=True) or request.form.to_dict()


def collection_fields(data):
    try:
        quantity = int(data.get("quantity", 1))
    except (TypeError, ValueError):
        return None, "Quantity must be a whole number."
    if not 1 <= quantity <= 1000:
        return None, "Quantity must be between 1 and 1000."
    condition = (data.get("condition") or DEFAULT_CONDITION).strip()
    if condition not in CONDITIONS:
        return None, "Select a valid condition."
    fields = {"quantity": quantity, "condition": condition}
    source_variant_id = (data.get("source_variant_id") or "").strip() or None
    variant_name = (data.get("variant_name") or "").strip()[:100]
    for field, allowed, default in (("variant", VARIANTS, "Normal"), ("language", LANGUAGES, DEFAULT_LANGUAGE)):
        if field == "variant" and source_variant_id:
            fields[field] = variant_name or "Imported Variant"
            fields["custom_variant"] = None
            fields["source_variant_id"] = source_variant_id
            continue
        value = (data.get(field) or default).strip()
        if value == "Other":
            other = (data.get(f"{field}_other") or "").strip()[:100]
            if not other:
                return None, f"Specify the other {field}."
            value = f"Other: {other}"
        elif value not in allowed:
            return None, f"Select a valid {field}."
        fields[field] = value
        if field == "variant": fields["custom_variant"] = other if value.startswith("Other: ") else None; fields["source_variant_id"] = None
    location = (data.get("storage_location") or DEFAULT_LOCATION).strip()[:100]
    if not location:
        return None, "Storage location is required."
    try:
        acquired = date.fromisoformat(data.get("acquisition_date") or date.today().isoformat()).isoformat()
    except ValueError:
        return None, "Date acquired must use YYYY-MM-DD."
    price = data.get("purchase_price")
    try:
        price = float(Decimal(str(price))) if price not in (None, "") else None
    except (InvalidOperation, ValueError):
        return None, "Purchase price must be a valid number."
    if price is not None and price < 0:
        return None, "Purchase price cannot be negative."
    ownership_type = (data.get("ownership_type") or "Raw").strip()
    if ownership_type not in {"Raw", "Graded"}: return None, "Select Raw or Graded ownership."
    fields.update({"ownership_type": ownership_type, "grading_company": None, "custom_grading_company": None, "grade": None, "certification_number": None})
    if ownership_type == "Graded":
        company = (data.get("grading_company") or "").strip()
        if company == "Other":
            custom = (data.get("custom_grading_company") or "").strip()[:100]
            if not custom: return None, "Specify the other grading company."
            fields["grading_company"], fields["custom_grading_company"] = "Other", custom
        elif company in GRADING_COMPANIES: fields["grading_company"] = company
        else: return None, "Select a valid grading company."
        try: grade = float(data.get("grade"))
        except (TypeError, ValueError): return None, "Grade must be a valid number."
        if not 0 <= grade <= 10: return None, "Grade must be between 0 and 10."
        fields["grade"] = grade
        fields["certification_number"] = (data.get("certification_number") or "").strip()[:100] or None
        fields["condition"] = ""
    purchase_date = (data.get("purchase_date") or "").strip()
    valuation_date = (data.get("last_valuation_date") or "").strip()
    try:
        purchase_date = date.fromisoformat(purchase_date).isoformat() if purchase_date else None
        valuation_date = date.fromisoformat(valuation_date).isoformat() if valuation_date else None
    except ValueError:
        return None, "Purchase and valuation dates must use YYYY-MM-DD."
    monetary_fields = {"estimated_value": data.get("estimated_value"), "insurance_value": data.get("insurance_value")}
    values = {}
    for name, value in monetary_fields.items():
        try:
            values[name] = float(Decimal(str(value))) if value not in (None, "") else None
        except (InvalidOperation, ValueError):
            return None, f"{name.replace('_', ' ').title()} must be a valid number."
        if values[name] is not None and values[name] < 0:
            return None, f"{name.replace('_', ' ').title()} cannot be negative."
    currency = (data.get("currency") or "USD").strip().upper()
    if len(currency) != 3 or not currency.isalpha():
        return None, "Currency must be a three-letter code."
    fields.update({
        "storage_location": location, "acquisition_date": acquired, "purchase_price": price,
        "purchase_date": purchase_date, "purchase_source": (data.get("purchase_source") or "").strip()[:100] or None,
        "estimated_value": values["estimated_value"], "previous_estimated_value": None,
        "last_valuation_date": valuation_date or (date.today().isoformat() if values["estimated_value"] is not None else None),
        "valuation_source": (data.get("valuation_source") or "Manual").strip()[:100] or None,
        "insurance_value": values["insurance_value"], "currency": currency,
        "notes": (data.get("notes") or "").strip()[:2000] or None,
    })
    return fields, None


def item_or_404(cur, item_id):
    return cur.execute("SELECT * FROM collection_items WHERE id = ? AND user_id = ?", (item_id, DEFAULT_USER_ID)).fetchone()


def wishlist_fields(data):
    priority = (data.get("priority") or "Medium").strip().title()
    if priority not in WISHLIST_PRIORITIES:
        return None, "Select a valid wishlist priority."
    desired_condition = (data.get("desired_condition") or "").strip()[:100] or None
    if desired_condition and desired_condition not in CONDITIONS:
        return None, "Select a valid desired condition."
    price = data.get("target_price")
    try:
        target_price = float(Decimal(str(price))) if price not in (None, "") else None
    except (InvalidOperation, ValueError):
        return None, "Target price must be a valid number."
    if target_price is not None and target_price < 0:
        return None, "Target price cannot be negative."
    return {
        "source_variant_id": (data.get("source_variant_id") or "").strip() or None,
        "priority": priority,
        "desired_condition": desired_condition,
        "target_price": target_price,
        "notes": (data.get("notes") or "").strip()[:2000] or None,
    }, None


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
        rows = conn.execute("SELECT * FROM collection_items WHERE user_id = ? AND card_id = ? ORDER BY updated_at DESC, id DESC", (DEFAULT_USER_ID, card_id)).fetchall()
    finally:
        conn.close()
    return jsonify({"items": [dict(row) for row in rows]})


@inventory.route("/collection/variants/<card_id>")
def collection_variants(card_id):
    conn = get_connection()
    try:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(variants)").fetchall()}
        if not {"source_variant_id", "name"}.issubset(columns):
            return jsonify({"variants": []})
        rows = conn.execute("SELECT source_variant_id, name, variant_type FROM variants WHERE card_id = ? ORDER BY CASE name WHEN 'Normal' THEN 1 WHEN 'Holo' THEN 2 WHEN 'Reverse Holo' THEN 3 WHEN '1st Edition' THEN 4 WHEN 'Unlimited' THEN 5 ELSE 99 END, name", (card_id,)).fetchall()
    finally:
        conn.close()
    return jsonify({"variants": [{"id": row["source_variant_id"], "name": row["name"] or row["variant_type"]} for row in rows if row["source_variant_id"]]})


@inventory.route("/wishlist/items/card/<card_id>")
def wishlist_items_for_card(card_id):
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM wishlist_items WHERE user_id = ? AND card_id = ? ORDER BY CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END, updated_at DESC", (DEFAULT_USER_ID, card_id)).fetchall()
    finally:
        conn.close()
    return jsonify({"items": [dict(row) for row in rows]})


@inventory.route("/wishlist/items/<card_id>", methods=["POST"])
def add_wishlist_item(card_id):
    fields, error = wishlist_fields(request_data())
    if error:
        return jsonify({"success": False, "error": error}), 400
    conn = get_connection()
    try:
        cur = conn.cursor()
        if cur.execute("SELECT 1 FROM cards WHERE id = ?", (card_id,)).fetchone() is None:
            return jsonify({"success": False, "error": "Card not found."}), 404
        if fields["source_variant_id"] and cur.execute("SELECT 1 FROM variants WHERE card_id = ? AND source_variant_id = ?", (card_id, fields["source_variant_id"])).fetchone() is None:
            return jsonify({"success": False, "error": "Selected variant does not belong to this card."}), 400
        existing = cur.execute("SELECT id FROM wishlist_items WHERE user_id = ? AND card_id = ? AND source_variant_id IS ?", (DEFAULT_USER_ID, card_id, fields["source_variant_id"])).fetchone()
        if existing:
            cur.execute("UPDATE wishlist_items SET priority = ?, desired_condition = ?, target_price = ?, notes = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (fields["priority"], fields["desired_condition"], fields["target_price"], fields["notes"], existing["id"]))
            item_id, status = existing["id"], 200
        else:
            cur.execute("INSERT INTO wishlist_items (user_id, card_id, source_variant_id, priority, desired_condition, target_price, notes) VALUES (?, ?, ?, ?, ?, ?, ?)", (DEFAULT_USER_ID, card_id, *fields.values()))
            item_id, status = cur.lastrowid, 201
        conn.commit()
    finally:
        conn.close()
    return jsonify({"success": True, "item_id": item_id}), status


@inventory.route("/wishlist/items/<int:item_id>", methods=["PATCH", "DELETE"])
def wishlist_item(item_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        item = cur.execute("SELECT * FROM wishlist_items WHERE id = ? AND user_id = ?", (item_id, DEFAULT_USER_ID)).fetchone()
        if item is None:
            return jsonify({"success": False, "error": "Wishlist item not found."}), 404
        if request.method == "DELETE":
            cur.execute("DELETE FROM wishlist_items WHERE id = ?", (item_id,))
        else:
            fields, error = wishlist_fields(request_data())
            if error:
                return jsonify({"success": False, "error": error}), 400
            cur.execute("UPDATE wishlist_items SET priority = ?, desired_condition = ?, target_price = ?, notes = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (fields["priority"], fields["desired_condition"], fields["target_price"], fields["notes"], item_id))
        conn.commit()
    finally:
        conn.close()
    return jsonify({"success": True})


@inventory.route("/inventory/add/<card_id>", methods=["POST"])
@inventory.route("/collection/items/<card_id>", methods=["POST"])
def add_card(card_id):
    fields, error = collection_fields(request_data())
    if error:
        return jsonify({"success": False, "error": error}), 400
    conn = get_connection()
    try:
        cur = conn.cursor()
        if cur.execute("SELECT 1 FROM cards WHERE id = ?", (card_id,)).fetchone() is None:
            return jsonify({"success": False, "error": "Card not found."}), 404
        if fields.get("source_variant_id") and cur.execute("SELECT 1 FROM variants WHERE card_id = ? AND source_variant_id = ?", (card_id, fields["source_variant_id"])).fetchone() is None:
            return jsonify({"success": False, "error": "Selected variant does not belong to this card."}), 400
        cur.execute("INSERT INTO collection_items (user_id, card_id, quantity, condition, variant, custom_variant, source_variant_id, language, ownership_type, grading_company, custom_grading_company, grade, certification_number, storage_location, acquisition_date, purchase_price, purchase_date, purchase_source, estimated_value, previous_estimated_value, last_valuation_date, valuation_source, insurance_value, currency, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (DEFAULT_USER_ID, card_id, *fields.values()))
        item_id = cur.lastrowid
        conn.commit()
        count = get_count(cur, card_id)
    finally:
        conn.close()
    return jsonify({"success": True, "item_id": item_id, "count": count}), 201


@inventory.route("/inventory/remove/<card_id>", methods=["POST"])
def remove_card(card_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        item = cur.execute("SELECT id, quantity FROM collection_items WHERE user_id = ? AND card_id = ? ORDER BY updated_at DESC, id DESC LIMIT 1", (DEFAULT_USER_ID, card_id)).fetchone()
        if item:
            if item["quantity"] > 1:
                cur.execute("UPDATE collection_items SET quantity = quantity - 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (item["id"],))
            else:
                cur.execute("DELETE FROM collection_items WHERE id = ?", (item["id"],))
            conn.commit()
        count = get_count(cur, card_id)
    finally:
        conn.close()
    return jsonify({"success": True, "count": count})


@inventory.route("/collection/items/<int:item_id>", methods=["PATCH", "DELETE"])
def collection_item(item_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        item = item_or_404(cur, item_id)
        if item is None:
            return jsonify({"success": False, "error": "Collection item not found."}), 404
        if request.method == "DELETE":
            cur.execute("DELETE FROM collection_items WHERE id = ?", (item_id,))
        else:
            fields, error = collection_fields(request_data())
            if error:
                return jsonify({"success": False, "error": error}), 400
            if fields["estimated_value"] != item["estimated_value"] and fields["estimated_value"] is not None:
                fields["previous_estimated_value"] = item["estimated_value"]
            else:
                fields["previous_estimated_value"] = item["previous_estimated_value"]
            cur.execute("UPDATE collection_items SET quantity = ?, condition = ?, variant = ?, custom_variant = ?, source_variant_id = ?, language = ?, ownership_type = ?, grading_company = ?, custom_grading_company = ?, grade = ?, certification_number = ?, storage_location = ?, acquisition_date = ?, purchase_price = ?, purchase_date = ?, purchase_source = ?, estimated_value = ?, previous_estimated_value = ?, last_valuation_date = ?, valuation_source = ?, insurance_value = ?, currency = ?, notes = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (*fields.values(), item_id))
        conn.commit()
        count = get_count(cur, item["card_id"])
    finally:
        conn.close()
    return jsonify({"success": True, "count": count})


@inventory.route("/collection/items/<int:item_id>/trade", methods=["PATCH"])
def collection_item_trade(item_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        item = item_or_404(cur, item_id)
        if item is None:
            return jsonify({"success": False, "error": "Collection item not found."}), 404
        trade = request_data().get("is_trade")
        if not isinstance(trade, bool):
            return jsonify({"success": False, "error": "is_trade must be true or false."}), 400
        cur.execute("UPDATE collection_items SET is_trade = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (int(trade), item_id))
        conn.commit()
    finally:
        conn.close()
    return jsonify({"success": True, "is_trade": trade})


@inventory.route("/collection/items/<int:item_id>/duplicate", methods=["POST"])
def duplicate_collection_item(item_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        item = item_or_404(cur, item_id)
        if item is None:
            return jsonify({"success": False, "error": "Collection item not found."}), 404
        cur.execute("INSERT INTO collection_items (user_id, card_id, quantity, condition, variant, custom_variant, source_variant_id, language, ownership_type, grading_company, custom_grading_company, grade, certification_number, storage_location, acquisition_date, purchase_price, purchase_date, purchase_source, estimated_value, previous_estimated_value, last_valuation_date, valuation_source, insurance_value, currency, notes, is_favorite, is_trade) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (DEFAULT_USER_ID, item["card_id"], item["quantity"], item["condition"], item["variant"], item["custom_variant"], item["source_variant_id"], item["language"], item["ownership_type"], item["grading_company"], item["custom_grading_company"], item["grade"], item["certification_number"], item["storage_location"], item["acquisition_date"], item["purchase_price"], item["purchase_date"], item["purchase_source"], item["estimated_value"], item["previous_estimated_value"], item["last_valuation_date"], item["valuation_source"], item["insurance_value"], item["currency"], item["notes"], item["is_favorite"], item["is_trade"]))
        duplicate_id = cur.lastrowid
        conn.commit()
        count = get_count(cur, item["card_id"])
    finally:
        conn.close()
    return jsonify({"success": True, "item_id": duplicate_id, "count": count}), 201
