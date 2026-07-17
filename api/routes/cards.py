import sqlite3

from flask import Blueprint, abort, jsonify, render_template, request

from config import DATABASE
from models.collection import DEFAULT_USER_ID
from services.master_set_progress import get_card_master_variants, get_set_master_progress


cards = Blueprint("cards", __name__)

DEFAULT_PAGE_SIZE = 24
MAX_PAGE_SIZE = 100

CARD_COLUMNS = """
    c.id, c.set_id, c.number, c.name, c.rarity, c.artist, c.hp, c.stage,
    c.evolves_from, c.regulation_mark, c.image_small, c.image_large,
    c.category, c.suffix, c.dex_id, c.illustrator, c.updated_at,
    s.name AS set_name, s.release_date AS set_release_date, s.printed_total,
    s.logo, s.symbol,
    COALESCE((
        SELECT SUM(ci.quantity)
        FROM collection_items ci
        WHERE ci.card_id = c.id AND ci.user_id = ?
    ), 0) AS owned
"""

SORT_COLUMNS = {
    "name": "c.name COLLATE NOCASE",
    "number": "CASE WHEN c.number GLOB '[0-9]*' THEN CAST(c.number AS INTEGER) END, c.number COLLATE NOCASE",
    "rarity": "c.rarity COLLATE NOCASE",
    "set": "s.name COLLATE NOCASE, CASE WHEN c.number GLOB '[0-9]*' THEN CAST(c.number AS INTEGER) END, c.number COLLATE NOCASE",
    "set_name": "s.name COLLATE NOCASE, CASE WHEN c.number GLOB '[0-9]*' THEN CAST(c.number AS INTEGER) END, c.number COLLATE NOCASE",
    "release_date": "s.release_date",
    "updated_at": "c.updated_at",
    "id": "c.id",
}


def get_connection():
    conn = sqlite3.connect(str(DATABASE))
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row):
    return dict(row) if row is not None else None


def positive_int(value, default, maximum=None):
    try:
        result = int(value)
    except (TypeError, ValueError):
        return default
    if result < 1:
        return default
    return min(result, maximum) if maximum else result


def get_pagination():
    return (
        positive_int(request.args.get("page"), 1),
        positive_int(request.args.get("per_page", request.args.get("limit")), DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE),
    )


def get_sorting(default="number"):
    sort = request.args.get("sort", default).lower()
    order = request.args.get("order", "asc").lower()
    sort = sort if sort in SORT_COLUMNS else default
    order = order if order in {"asc", "desc"} else "asc"
    return sort, order, f"{SORT_COLUMNS[sort]} {order.upper()}, c.id ASC"


def get_filters(include_search=True):
    clauses, params = [], []
    for query_name, column in (("set_id", "c.set_id"), ("series_id", "s.series_id"), ("category", "c.category"), ("rarity", "c.rarity")):
        value = request.args.get(query_name)
        if value:
            clauses.append(f"{column} = ?")
            params.append(value)

    owned = request.args.get("owned")
    if owned is not None:
        normalized = owned.strip().lower()
        ownership = "SELECT 1 FROM collection_items ci WHERE ci.card_id = c.id AND ci.user_id = ? AND ci.quantity > 0"
        if normalized in {"1", "true", "yes"}:
            clauses.append(f"EXISTS ({ownership})")
            params.append(DEFAULT_USER_ID)
        elif normalized in {"0", "false", "no"}:
            clauses.append(f"NOT EXISTS ({ownership})")
            params.append(DEFAULT_USER_ID)

    if include_search:
        query = request.args.get("q", request.args.get("query", request.args.get("search", ""))).strip()
        if query:
            like = f"%{query}%"
            clauses.append("(c.name LIKE ? COLLATE NOCASE OR c.number LIKE ? OR c.id LIKE ? OR s.name LIKE ? COLLATE NOCASE)")
            params.extend([like, like, like, like])
    return clauses, params


def where_clause(clauses):
    return f"WHERE {' AND '.join(clauses)}" if clauses else ""


def fetch_cards(conn, clauses, params, order_by, page, per_page):
    filters = where_clause(clauses)
    total = conn.execute(
        f"SELECT COUNT(*) FROM cards c JOIN sets s ON s.id = c.set_id {filters}", params
    ).fetchone()[0]
    rows = conn.execute(
        f"""
        SELECT {CARD_COLUMNS}
        FROM cards c JOIN sets s ON s.id = c.set_id
        {filters}
        ORDER BY {order_by}
        LIMIT ? OFFSET ?
        """,
        [DEFAULT_USER_ID, *params, per_page, (page - 1) * per_page],
    ).fetchall()
    return [row_to_dict(row) for row in rows], total


def paginated_response(cards_list, total, page, per_page, sort, order):
    pages = (total + per_page - 1) // per_page if total else 0
    return jsonify({
        "cards": cards_list,
        "pagination": {
            "page": page, "per_page": per_page, "total": total, "total_pages": pages,
            "has_next": page < pages, "has_previous": page > 1 and pages > 0,
        },
        "sort": sort,
        "order": order,
    })


@cards.route("/api/cards")
def api_cards():
    page, per_page = get_pagination()
    sort, order, order_by = get_sorting()
    filters, params = get_filters()
    conn = get_connection()
    try:
        cards_list, total = fetch_cards(conn, filters, params, order_by, page, per_page)
    finally:
        conn.close()
    return paginated_response(cards_list, total, page, per_page, sort, order)


@cards.route("/api/cards/search")
def search_cards():
    page, per_page = get_pagination()
    sort, order, order_by = get_sorting("name")
    filters, params = get_filters()
    conn = get_connection()
    try:
        cards_list, total = fetch_cards(conn, filters, params, order_by, page, per_page)
    finally:
        conn.close()
    return paginated_response(cards_list, total, page, per_page, sort, order)


@cards.route("/api/cards/random")
def random_card():
    filters, params = get_filters()
    conn = get_connection()
    try:
        row = conn.execute(
            f"SELECT {CARD_COLUMNS} FROM cards c JOIN sets s ON s.id = c.set_id {where_clause(filters)} ORDER BY RANDOM() LIMIT 1",
            [DEFAULT_USER_ID, *params],
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return jsonify({"error": "No cards found"}), 404
    return jsonify({"card": row_to_dict(row)})


@cards.route("/api/cards/recent")
def recent_cards():
    page, per_page = get_pagination()
    filters, params = get_filters()
    conn = get_connection()
    try:
        cards_list, total = fetch_cards(conn, filters, params, "c.updated_at IS NULL ASC, c.updated_at DESC, c.id DESC", page, per_page)
    finally:
        conn.close()
    return paginated_response(cards_list, total, page, per_page, "updated_at", "desc")


@cards.route("/api/cards/<card_id>")
def api_card_detail(card_id):
    conn = get_connection()
    try:
        row = conn.execute(
            f"SELECT {CARD_COLUMNS} FROM cards c JOIN sets s ON s.id = c.set_id WHERE c.id = ?",
            (DEFAULT_USER_ID, card_id),
        ).fetchone()
        if row is None:
            return jsonify({"error": "Card not found"}), 404
        card = row_to_dict(row)
        details = {
            "abilities": "SELECT ability_type, name, text FROM abilities WHERE card_id = ? ORDER BY id",
            "attacks": "SELECT attack_order, name, damage, text FROM attacks WHERE card_id = ? ORDER BY attack_order, id",
            "weaknesses": "SELECT type, value FROM weaknesses WHERE card_id = ? ORDER BY id",
            "resistances": "SELECT type, value FROM resistances WHERE card_id = ? ORDER BY id",
            "retreat_cost": "SELECT energy, position FROM retreat_cost WHERE card_id = ? ORDER BY position, id",
        }
        for name, query in details.items():
            card[name] = [row_to_dict(item) for item in conn.execute(query, (card_id,)).fetchall()]
    finally:
        conn.close()
    return jsonify({"card": card})


@cards.route("/sets/<set_id>")
def cards_by_set(set_id):
    conn = get_connection()
    try:
        set_info = conn.execute("SELECT id, name FROM sets WHERE id = ?", (set_id,)).fetchone()
        if set_info is None:
            abort(404, description="Set not found")
        cards_list = conn.execute(
            """
            SELECT c.id, c.number, c.name, c.rarity, c.image_small, c.hp, c.category, c.artist,
                   COALESCE(SUM(ci.quantity), 0) AS owned
            FROM cards c
            LEFT JOIN collection_items ci ON ci.card_id = c.id AND ci.user_id = ?
            WHERE c.set_id = ?
            GROUP BY c.id, c.number, c.name, c.rarity, c.image_small, c.hp, c.category, c.artist
            ORDER BY CASE WHEN c.number GLOB '[0-9]*' THEN CAST(c.number AS INTEGER) END, c.number, c.id
            """,
            (DEFAULT_USER_ID, set_id),
        ).fetchall()
        master_progress = get_set_master_progress(conn, set_id, DEFAULT_USER_ID)
    finally:
        conn.close()
    total_cards = len(cards_list)
    owned_cards = sum(1 for card in cards_list if card["owned"] > 0)
    return render_template(
        "cards.html", title=set_info["name"], set_name=set_info["name"], cards=cards_list,
        total_cards=total_cards, owned_cards=owned_cards, missing_cards=total_cards - owned_cards,
        percent_complete=round((owned_cards / total_cards) * 100) if total_cards else 0,
        master_progress=master_progress,
    )


@cards.route("/card/<card_id>")
def card_detail(card_id):
    conn = get_connection()
    try:
        card = conn.execute(
            f"SELECT {CARD_COLUMNS} FROM cards c JOIN sets s ON s.id = c.set_id WHERE c.id = ?",
            (DEFAULT_USER_ID, card_id),
        ).fetchone()
        if card is None:
            abort(404, description="Card not found")
        abilities = conn.execute("SELECT ability_type, name, text FROM abilities WHERE card_id = ? ORDER BY id", (card_id,)).fetchall()
        attacks = [row_to_dict(row) for row in conn.execute("SELECT id, attack_order, name, damage, text FROM attacks WHERE card_id = ? ORDER BY attack_order, id", (card_id,)).fetchall()]
        attack_ids = [attack["id"] for attack in attacks]
        costs_by_attack = {attack_id: [] for attack_id in attack_ids}
        if attack_ids:
            placeholders = ", ".join("?" for _ in attack_ids)
            for cost in conn.execute(f"SELECT attack_id, energy FROM attack_cost WHERE attack_id IN ({placeholders}) ORDER BY attack_id, position, id", attack_ids).fetchall():
                costs_by_attack[cost["attack_id"]].append(cost["energy"])
        for attack in attacks:
            attack["cost"] = costs_by_attack[attack["id"]]
        card_types = [row["type"] for row in conn.execute("SELECT type FROM card_types WHERE card_id = ? ORDER BY id", (card_id,)).fetchall()]
        subtypes = [row["subtype"] for row in conn.execute("SELECT subtype FROM card_subtypes WHERE card_id = ? ORDER BY id", (card_id,)).fetchall()]
        weaknesses = conn.execute("SELECT type, value FROM weaknesses WHERE card_id = ? ORDER BY id", (card_id,)).fetchall()
        resistances = conn.execute("SELECT type, value FROM resistances WHERE card_id = ? ORDER BY id", (card_id,)).fetchall()
        retreat = conn.execute("SELECT energy, position FROM retreat_cost WHERE card_id = ? ORDER BY position, id", (card_id,)).fetchall()
        owned_items = conn.execute(
            """
            SELECT id, quantity, condition, variant, custom_variant, ownership_type, is_trade,
                   grading_company, custom_grading_company, grade, certification_number,
                   storage_location, acquisition_date, purchase_price, purchase_date, purchase_source,
                   estimated_value, previous_estimated_value, last_valuation_date, valuation_source,
                   insurance_value, currency, notes
            FROM collection_items
            WHERE user_id = ? AND card_id = ?
            ORDER BY updated_at DESC, id DESC
            """,
            (DEFAULT_USER_ID, card_id),
        ).fetchall()
        master_variants = get_card_master_variants(conn, card_id, DEFAULT_USER_ID)
        wishlist_items = conn.execute("SELECT id, source_variant_id, priority, desired_condition, target_price, notes FROM wishlist_items WHERE user_id = ? AND card_id = ? ORDER BY CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END", (DEFAULT_USER_ID, card_id)).fetchall()
        siblings = conn.execute(
            "SELECT id, name FROM cards WHERE set_id = ? ORDER BY CASE WHEN number GLOB '[0-9]*' THEN CAST(number AS INTEGER) END, number, id",
            (card["set_id"],),
        ).fetchall()
    finally:
        conn.close()
    position = [row["id"] for row in siblings].index(card_id)
    return render_template(
        "card_detail.html", title=card["name"], card=card, abilities=abilities, attacks=attacks,
        card_types=card_types, subtypes=subtypes,
        weaknesses=weaknesses, resistances=resistances, retreat=retreat,
        owned_items=owned_items, master_variants=master_variants,
        wishlist_items=wishlist_items,
        previous_card=siblings[position - 1] if position else None,
        next_card=siblings[position + 1] if position + 1 < len(siblings) else None,
    )
