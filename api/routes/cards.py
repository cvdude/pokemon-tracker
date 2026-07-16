from flask import Blueprint, abort, jsonify, render_template, request
import sqlite3

from config import DATABASE


cards = Blueprint("cards", __name__)


DEFAULT_PAGE_SIZE = 24
MAX_PAGE_SIZE = 100

CARD_COLUMNS = """
    c.id,
    c.set_id,
    c.number,
    c.name,
    c.rarity,
    c.artist,
    c.hp,
    c.stage,
    c.evolves_from,
    c.regulation_mark,
    c.image_small,
    c.image_large,
    c.category,
    c.suffix,
    c.dex_id,
    c.illustrator,
    c.updated_at,
    s.name AS set_name,
    s.release_date AS set_release_date,
    s.printed_total,
    s.logo,
    s.symbol,
    COALESCE((
        SELECT SUM(i.quantity)
        FROM inventory i
        WHERE i.card_id = c.id AND i.user_id = 1
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
    """Return a SQLite connection configured for dictionary-like rows."""
    conn = sqlite3.connect(str(DATABASE))
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row):
    """Convert a SQLite row to a JSON-safe dictionary."""
    return dict(row) if row is not None else None


def positive_int(value, default, maximum=None):
    """Read a positive integer query value without allowing invalid pagination."""
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default

    if parsed < 1:
        return default
    if maximum is not None:
        return min(parsed, maximum)
    return parsed


def get_pagination():
    """Support both per_page and limit for existing API consumers."""
    page = positive_int(request.args.get("page"), 1)
    per_page = positive_int(
        request.args.get("per_page", request.args.get("limit")),
        DEFAULT_PAGE_SIZE,
        MAX_PAGE_SIZE,
    )
    return page, per_page


def get_sorting(default="number"):
    """Build a safe ORDER BY clause from supported sort and order values."""
    sort = request.args.get("sort", default).lower()
    order = request.args.get("order", "asc").lower()

    if sort not in SORT_COLUMNS:
        sort = default
    if order not in {"asc", "desc"}:
        order = "asc"

    return sort, order, f"{SORT_COLUMNS[sort]} {order.upper()}, c.id ASC"


def get_filters(include_search=True):
    """Return WHERE fragments and values for the supported card filters."""
    clauses = []
    params = []

    set_id = request.args.get("set_id")
    if set_id:
        clauses.append("c.set_id = ?")
        params.append(set_id)

    series_id = request.args.get("series_id")
    if series_id:
        clauses.append("s.series_id = ?")
        params.append(series_id)

    category = request.args.get("category")
    if category:
        clauses.append("c.category = ?")
        params.append(category)

    rarity = request.args.get("rarity")
    if rarity:
        clauses.append("c.rarity = ?")
        params.append(rarity)

    owned = request.args.get("owned")
    if owned is not None:
        normalized_owned = owned.strip().lower()
        if normalized_owned in {"1", "true", "yes"}:
            clauses.append("EXISTS (SELECT 1 FROM inventory i WHERE i.card_id = c.id AND i.user_id = 1 AND i.quantity > 0)")
        elif normalized_owned in {"0", "false", "no"}:
            clauses.append("NOT EXISTS (SELECT 1 FROM inventory i WHERE i.card_id = c.id AND i.user_id = 1 AND i.quantity > 0)")

    if include_search:
        query = request.args.get("q", request.args.get("query", request.args.get("search", ""))).strip()
        if query:
            like_query = f"%{query}%"
            clauses.append("(c.name LIKE ? COLLATE NOCASE OR c.number LIKE ? OR c.id LIKE ? OR s.name LIKE ? COLLATE NOCASE)")
            params.extend([like_query, like_query, like_query, like_query])

    return clauses, params


def where_clause(clauses):
    return f"WHERE {' AND '.join(clauses)}" if clauses else ""


def fetch_cards(conn, clauses, params, order_by, page, per_page):
    """Fetch a page of cards and its total count using one shared filter set."""
    filters = where_clause(clauses)
    total = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM cards c
        JOIN sets s ON s.id = c.set_id
        {filters}
        """,
        params,
    ).fetchone()[0]

    offset = (page - 1) * per_page
    rows = conn.execute(
        f"""
        SELECT {CARD_COLUMNS}
        FROM cards c
        JOIN sets s ON s.id = c.set_id
        {filters}
        ORDER BY {order_by}
        LIMIT ? OFFSET ?
        """,
        [*params, per_page, offset],
    ).fetchall()

    return [row_to_dict(row) for row in rows], total


def paginated_response(cards_list, total, page, per_page, sort, order):
    total_pages = (total + per_page - 1) // per_page if total else 0
    return jsonify(
        {
            "cards": cards_list,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1 and total_pages > 0,
            },
            "sort": sort,
            "order": order,
        }
    )


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
    sort, order, order_by = get_sorting(default="name")
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
            f"""
            SELECT {CARD_COLUMNS}
            FROM cards c
            JOIN sets s ON s.id = c.set_id
            {where_clause(filters)}
            ORDER BY RANDOM()
            LIMIT 1
            """,
            params,
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
    order_by = "c.updated_at IS NULL ASC, c.updated_at DESC, c.id DESC"

    conn = get_connection()
    try:
        cards_list, total = fetch_cards(conn, filters, params, order_by, page, per_page)
    finally:
        conn.close()

    return paginated_response(cards_list, total, page, per_page, "updated_at", "desc")


@cards.route("/api/cards/<card_id>")
def api_card_detail(card_id):
    conn = get_connection()
    try:
        row = conn.execute(
            f"""
            SELECT {CARD_COLUMNS}
            FROM cards c
            JOIN sets s ON s.id = c.set_id
            WHERE c.id = ?
            """,
            (card_id,),
        ).fetchone()

        if row is None:
            return jsonify({"error": "Card not found"}), 404

        card = row_to_dict(row)
        card["abilities"] = [row_to_dict(item) for item in conn.execute(
            "SELECT ability_type, name, text FROM abilities WHERE card_id = ? ORDER BY id", (card_id,)
        ).fetchall()]
        card["attacks"] = [row_to_dict(item) for item in conn.execute(
            "SELECT attack_order, name, damage, text FROM attacks WHERE card_id = ? ORDER BY attack_order, id", (card_id,)
        ).fetchall()]
        card["weaknesses"] = [row_to_dict(item) for item in conn.execute(
            "SELECT type, value FROM weaknesses WHERE card_id = ? ORDER BY id", (card_id,)
        ).fetchall()]
        card["resistances"] = [row_to_dict(item) for item in conn.execute(
            "SELECT type, value FROM resistances WHERE card_id = ? ORDER BY id", (card_id,)
        ).fetchall()]
        card["retreat_cost"] = [row_to_dict(item) for item in conn.execute(
            "SELECT energy, position FROM retreat_cost WHERE card_id = ? ORDER BY position, id", (card_id,)
        ).fetchall()]
    finally:
        conn.close()

    return jsonify({"card": card})


@cards.route("/sets/<set_id>")
def cards_by_set(set_id):
    conn = get_connection()
    try:
        set_info = conn.execute(
            "SELECT id, name FROM sets WHERE id = ?", (set_id,)
        ).fetchone()
        if set_info is None:
            abort(404, description="Set not found")

        cards_list = conn.execute(
            """
            SELECT
                c.id, c.number, c.name, c.rarity, c.image_small, c.hp, c.category, c.artist,
                COALESCE(SUM(i.quantity), 0) AS owned
            FROM cards c
            LEFT JOIN inventory i ON c.id = i.card_id AND i.user_id = 1
            WHERE c.set_id = ?
            GROUP BY c.id, c.number, c.name, c.rarity, c.image_small, c.hp, c.category, c.artist
            ORDER BY CASE WHEN c.number GLOB '[0-9]*' THEN CAST(c.number AS INTEGER) END, c.number, c.id
            """,
            (set_id,),
        ).fetchall()
    finally:
        conn.close()

    total_cards = len(cards_list)
    owned_cards = sum(1 for card in cards_list if card["owned"] > 0)
    missing_cards = total_cards - owned_cards
    percent_complete = round((owned_cards / total_cards) * 100) if total_cards else 0

    return render_template(
        "cards.html",
        title=set_info["name"],
        set_name=set_info["name"],
        cards=cards_list,
        total_cards=total_cards,
        owned_cards=owned_cards,
        missing_cards=missing_cards,
        percent_complete=percent_complete,
    )


@cards.route("/card/<card_id>")
def card_detail(card_id):
    conn = get_connection()
    try:
        card = conn.execute(
            f"""
            SELECT {CARD_COLUMNS}
            FROM cards c
            JOIN sets s ON s.id = c.set_id
            WHERE c.id = ?
            """,
            (card_id,),
        ).fetchone()
        if card is None:
            abort(404, description="Card not found")

        abilities = conn.execute(
            "SELECT ability_type, name, text FROM abilities WHERE card_id = ? ORDER BY id", (card_id,)
        ).fetchall()
        attacks = conn.execute(
            "SELECT attack_order, name, damage, text FROM attacks WHERE card_id = ? ORDER BY attack_order, id", (card_id,)
        ).fetchall()
        weaknesses = conn.execute(
            "SELECT type, value FROM weaknesses WHERE card_id = ? ORDER BY id", (card_id,)
        ).fetchall()
        resistances = conn.execute(
            "SELECT type, value FROM resistances WHERE card_id = ? ORDER BY id", (card_id,)
        ).fetchall()
        retreat = conn.execute(
            "SELECT energy, position FROM retreat_cost WHERE card_id = ? ORDER BY position, id", (card_id,)
        ).fetchall()

        siblings = conn.execute(
            """
            SELECT id, name
            FROM cards
            WHERE set_id = ?
            ORDER BY CASE WHEN number GLOB '[0-9]*' THEN CAST(number AS INTEGER) END, number, id
            """,
            (card["set_id"],),
        ).fetchall()
    finally:
        conn.close()

    sibling_ids = [row["id"] for row in siblings]
    position = sibling_ids.index(card_id)
    previous_card = siblings[position - 1] if position else None
    next_card = siblings[position + 1] if position + 1 < len(siblings) else None

    return render_template(
        "card_detail.html",
        title=card["name"],
        card=card,
        ability=abilities[0] if abilities else None,
        attacks=attacks,
        weaknesses=weaknesses,
        resistances=resistances,
        retreat=retreat,
        previous_card=previous_card,
        next_card=next_card,
    )
