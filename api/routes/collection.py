import sqlite3
from urllib.parse import urlencode

from flask import Blueprint, render_template, request

from config import DATABASE
from models.collection import DEFAULT_USER_ID
from models.settings import get_settings


collection = Blueprint("collection", __name__)

PAGE_SIZE = 250
SORT_COLUMNS = {
    "name": "c.name COLLATE NOCASE",
    "set": "s.name COLLATE NOCASE",
    "number": "CASE WHEN c.number GLOB '[0-9]*' THEN CAST(c.number AS INTEGER) END, c.number COLLATE NOCASE",
    "rarity": "c.rarity COLLATE NOCASE",
    "quantity": "COALESCE(ct.total_quantity, 0)",
    "updated": "ct.last_updated",
}


def _has_imported_variant_ids(conn):
    return "source_variant_id" in {
        row["name"] for row in conn.execute("PRAGMA table_info(variants)").fetchall()
    }


def _master_filter(value):
    """Build a card-level Master Set completion expression."""
    fallback_complete = "COALESCE(ct.total_quantity, 0) > 0"
    if value not in {"complete", "incomplete"}:
        return None
    complete = f"""
        CASE WHEN EXISTS (
            SELECT 1 FROM variants v
            WHERE v.card_id = c.id AND v.source_variant_id IS NOT NULL AND v.source_variant_id <> ''
        ) THEN NOT EXISTS (
            SELECT 1 FROM variants v
            WHERE v.card_id = c.id AND v.source_variant_id IS NOT NULL AND v.source_variant_id <> ''
              AND NOT EXISTS (
                  SELECT 1 FROM collection_items ci
                  WHERE ci.user_id = ? AND ci.card_id = c.id AND ci.quantity > 0
                    AND (ci.source_variant_id = v.source_variant_id
                         OR ((ci.source_variant_id IS NULL OR ci.source_variant_id = '')
                             AND LOWER(TRIM(COALESCE(ci.custom_variant, ci.variant))) = LOWER(TRIM(COALESCE(v.name, v.variant_type)))))
              )
        ) ELSE {fallback_complete} END
    """
    return complete if value == "complete" else f"NOT ({complete})"


@collection.route("/collection")
def collection_page():
    preferences = get_settings(DEFAULT_USER_ID)
    has_query_filters = any(name in request.args for name in ("q", "ownership", "duplicates", "grading", "master", "has_notes", "wishlist", "trade", "wishlist_priority", "never_valued", "value_changed", "purchased_month", "purchased_year", "sort", "order"))
    defaults = preferences["default_filters"] if not has_query_filters else {}
    query = request.args.get("q", "").strip()
    ownership = request.args.get("ownership", defaults.get("ownership", "owned")).lower()
    ownership = ownership if ownership in {"owned", "missing", "all"} else "owned"
    duplicates = request.args.get("duplicates", defaults.get("duplicates", "")).lower() in {"1", "true", "yes"} if isinstance(defaults.get("duplicates", ""), str) else bool(defaults.get("duplicates", False))
    grading = request.args.get("grading", "").lower()
    master = request.args.get("master", "").lower()
    has_notes = request.args.get("has_notes", defaults.get("has_notes", "")).lower() in {"1", "true", "yes"} if isinstance(defaults.get("has_notes", ""), str) else bool(defaults.get("has_notes", False))
    wishlist = request.args.get("wishlist", defaults.get("wishlist", "")).lower() in {"1", "true", "yes"} if isinstance(defaults.get("wishlist", ""), str) else bool(defaults.get("wishlist", False))
    trade = request.args.get("trade", defaults.get("trade", "")).lower() in {"1", "true", "yes"} if isinstance(defaults.get("trade", ""), str) else bool(defaults.get("trade", False))
    wishlist_priority = request.args.get("wishlist_priority", "").title()
    wishlist_priority = wishlist_priority if wishlist_priority in {"Low", "Medium", "High"} else ""
    never_valued = request.args.get("never_valued", "").lower() in {"1", "true", "yes"}
    value_changed = request.args.get("value_changed", "").lower() in {"1", "true", "yes"}
    purchased_month = request.args.get("purchased_month", "").lower() in {"1", "true", "yes"}
    purchased_year = request.args.get("purchased_year", "").lower() in {"1", "true", "yes"}
    sort = request.args.get("sort", preferences["default_sort"]).lower()
    sort = sort if sort in SORT_COLUMNS else "name"
    order = request.args.get("order", preferences["default_order"]).lower()
    order = order if order in {"asc", "desc"} else "asc"

    clauses, params = [], [DEFAULT_USER_ID]
    if ownership == "owned":
        clauses.append("COALESCE(ct.total_quantity, 0) > 0")
    elif ownership == "missing":
        clauses.append("COALESCE(ct.total_quantity, 0) = 0")
    if duplicates:
        clauses.append("COALESCE(ct.total_quantity, 0) > 1")
    if grading == "graded":
        clauses.append("COALESCE(ct.graded_items, 0) > 0")
    elif grading == "ungraded":
        clauses.append("COALESCE(ct.ungraded_items, 0) > 0")
    if has_notes:
        clauses.append("COALESCE(ct.has_notes, 0) > 0")
    if wishlist:
        clauses.append("COALESCE(wt.item_count, 0) > 0")
    if wishlist_priority:
        clauses.append("wt.priority = ?")
        params.append(wishlist_priority)
    if trade:
        clauses.append("COALESCE(ct.trade_quantity, 0) > 0")
    if never_valued:
        clauses.append("COALESCE(ct.total_quantity, 0) > 0 AND COALESCE(ct.valued_items, 0) = 0")
    if value_changed:
        clauses.append("COALESCE(ct.value_changed_items, 0) > 0")
    if purchased_month:
        clauses.append("COALESCE(ct.purchased_month_items, 0) > 0")
    if purchased_year:
        clauses.append("COALESCE(ct.purchased_year_items, 0) > 0")
    if query:
        like = f"%{query}%"
        clauses.append(
            """(
                c.name LIKE ? COLLATE NOCASE OR c.number LIKE ? OR c.id LIKE ?
                OR s.name LIKE ? COLLATE NOCASE OR se.name LIKE ? COLLATE NOCASE
                OR c.hp LIKE ? OR c.rarity LIKE ? COLLATE NOCASE
                OR c.artist LIKE ? COLLATE NOCASE OR c.illustrator LIKE ? COLLATE NOCASE
                OR EXISTS (SELECT 1 FROM card_types t WHERE t.card_id = c.id AND t.type LIKE ? COLLATE NOCASE)
                OR EXISTS (SELECT 1 FROM collection_items ci WHERE ci.card_id = c.id AND ci.user_id = ?
                           AND (ci.variant LIKE ? COLLATE NOCASE OR ci.condition LIKE ? COLLATE NOCASE
                                OR CAST(ci.grade AS TEXT) LIKE ? OR ci.storage_location LIKE ? COLLATE NOCASE))
            )"""
        )
        params.extend([like, like, like, like, like, like, like, like, like, like, DEFAULT_USER_ID, like, like, like, like])

    conn = sqlite3.connect(str(DATABASE))
    conn.row_factory = sqlite3.Row
    try:
        if master in {"complete", "incomplete"}:
            if _has_imported_variant_ids(conn):
                clauses.append(_master_filter(master))
                params.append(DEFAULT_USER_ID)
            elif master == "complete":
                clauses.append("COALESCE(ct.total_quantity, 0) > 0")
            else:
                clauses.append("COALESCE(ct.total_quantity, 0) = 0")
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            WITH card_totals AS (
                SELECT card_id, SUM(quantity) AS total_quantity, MAX(updated_at) AS last_updated,
                       SUM(CASE WHEN ownership_type = 'Graded' THEN 1 ELSE 0 END) AS graded_items,
                       SUM(CASE WHEN ownership_type = 'Raw' THEN 1 ELSE 0 END) AS ungraded_items,
                       SUM(CASE WHEN is_trade = 1 THEN quantity ELSE 0 END) AS trade_quantity,
                       SUM(CASE WHEN estimated_value IS NOT NULL THEN 1 ELSE 0 END) AS valued_items,
                       SUM(CASE WHEN estimated_value IS NOT NULL AND previous_estimated_value IS NOT NULL AND estimated_value <> previous_estimated_value THEN 1 ELSE 0 END) AS value_changed_items,
                       SUM(CASE WHEN purchase_date >= date('now', 'start of month') THEN 1 ELSE 0 END) AS purchased_month_items,
                       SUM(CASE WHEN purchase_date >= date('now', 'start of year') THEN 1 ELSE 0 END) AS purchased_year_items,
                       MAX(CASE WHEN TRIM(COALESCE(notes, '')) <> '' THEN 1 ELSE 0 END) AS has_notes
                FROM collection_items
                WHERE user_id = ? AND quantity > 0
                GROUP BY card_id
            ), wishlist_totals AS (
                SELECT card_id, COUNT(*) AS item_count,
                       MIN(CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END) AS priority_rank,
                       CASE MIN(CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END)
                           WHEN 1 THEN 'High' WHEN 2 THEN 'Medium' ELSE 'Low' END AS priority
                FROM wishlist_items WHERE user_id = ? GROUP BY card_id
            )
            SELECT c.id AS card_id, c.name, c.number, c.rarity, c.hp, c.category, c.artist,
                   c.image_small, s.id AS set_id, s.name AS set_name, se.name AS series_name,
                   COALESCE(ct.total_quantity, 0) AS quantity, COALESCE(ct.trade_quantity, 0) AS trade_quantity,
                   COALESCE(wt.item_count, 0) AS wishlist_count, wt.priority AS wishlist_priority, ct.last_updated,
                   COUNT(*) OVER () AS filtered_total
            FROM cards c
            JOIN sets s ON s.id = c.set_id
            LEFT JOIN series se ON se.id = s.series_id
            LEFT JOIN card_totals ct ON ct.card_id = c.id
            LEFT JOIN wishlist_totals wt ON wt.card_id = c.id
            {where}
            ORDER BY {SORT_COLUMNS[sort]} {order.upper()}, c.id ASC
            LIMIT {PAGE_SIZE}
            """,
            [DEFAULT_USER_ID, DEFAULT_USER_ID, *params[1:]],
        ).fetchall()
    finally:
        conn.close()

    filters = {
        "q": query, "ownership": ownership, "duplicates": duplicates, "grading": grading,
        "master": master, "has_notes": has_notes, "wishlist": wishlist, "trade": trade,
        "wishlist_priority": wishlist_priority, "never_valued": never_valued, "value_changed": value_changed,
        "purchased_month": purchased_month, "purchased_year": purchased_year, "sort": sort, "order": order,
    }
    sort_urls = {}
    for key in SORT_COLUMNS:
        values = {name: value for name, value in filters.items() if value not in {"", False}}
        values["sort"] = key
        values["order"] = "desc" if key == sort and order == "asc" else "asc"
        sort_urls[key] = f"/collection?{urlencode(values)}"
    result_count = rows[0]["filtered_total"] if rows else 0
    return render_template(
        "collection.html", title="Advanced Collection Search", results=rows, filters=filters,
        sort_urls=sort_urls, result_count=result_count, displayed_count=len(rows), page_size=PAGE_SIZE,
    )
