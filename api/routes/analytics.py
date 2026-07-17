import sqlite3
from urllib.parse import urlencode

from flask import Blueprint, render_template

from config import DATABASE
from models.collection import DEFAULT_USER_ID


analytics = Blueprint("analytics", __name__)


def _link(query="", **filters):
    values = {"ownership": "owned", **filters}
    if query:
        values["q"] = query
    return f"/collection?{urlencode(values)}"


def _rows(conn, query, params=(DEFAULT_USER_ID,), link_key=None, link_filters=None):
    rows = [dict(row) for row in conn.execute(query, params).fetchall()]
    if link_key:
        for row in rows:
            row["link"] = _link(row[link_key], **(link_filters or {}))
    return rows


@analytics.route("/analytics")
def analytics_page():
    conn = sqlite3.connect(str(DATABASE))
    conn.row_factory = sqlite3.Row
    try:
        series = _rows(conn, """
            SELECT COALESCE(se.name, 'Unknown') AS label, COUNT(DISTINCT c.id) AS cards, SUM(ci.quantity) AS quantity
            FROM collection_items ci JOIN cards c ON c.id = ci.card_id JOIN sets s ON s.id = c.set_id
            LEFT JOIN series se ON se.id = s.series_id
            WHERE ci.user_id = ? AND ci.quantity > 0 GROUP BY se.id, se.name ORDER BY quantity DESC, label LIMIT 20
        """, link_key="label")
        sets = _rows(conn, """
            SELECT s.id, s.name AS label, COUNT(DISTINCT c.id) AS cards, SUM(ci.quantity) AS quantity
            FROM collection_items ci JOIN cards c ON c.id = ci.card_id JOIN sets s ON s.id = c.set_id
            WHERE ci.user_id = ? AND ci.quantity > 0 GROUP BY s.id, s.name ORDER BY quantity DESC, label LIMIT 20
        """, link_key="label")
        types = _rows(conn, """
            SELECT COALESCE(t.type, 'Unspecified') AS label, COUNT(DISTINCT c.id) AS cards, SUM(ci.quantity) AS quantity
            FROM collection_items ci JOIN cards c ON c.id = ci.card_id LEFT JOIN card_types t ON t.card_id = c.id
            WHERE ci.user_id = ? AND ci.quantity > 0 GROUP BY t.type ORDER BY quantity DESC, label
        """, link_key="label")
        rarity = _rows(conn, """
            SELECT COALESCE(c.rarity, 'Unspecified') AS label, COUNT(DISTINCT c.id) AS cards, SUM(ci.quantity) AS quantity
            FROM collection_items ci JOIN cards c ON c.id = ci.card_id
            WHERE ci.user_id = ? AND ci.quantity > 0 GROUP BY c.rarity ORDER BY quantity DESC, label
        """, link_key="label")
        stage = _rows(conn, """
            SELECT COALESCE(c.stage, 'Unspecified') AS label, COUNT(DISTINCT c.id) AS cards, SUM(ci.quantity) AS quantity
            FROM collection_items ci JOIN cards c ON c.id = ci.card_id
            WHERE ci.user_id = ? AND ci.quantity > 0 GROUP BY c.stage ORDER BY quantity DESC, label
        """, link_key="label")
        condition = _rows(conn, """
            SELECT CASE WHEN ci.ownership_type = 'Graded' THEN 'Graded' ELSE COALESCE(NULLIF(ci.condition, ''), 'Unspecified') END AS label,
                   SUM(ci.quantity) AS quantity
            FROM collection_items ci WHERE ci.user_id = ? AND ci.quantity > 0 GROUP BY label ORDER BY quantity DESC, label
        """, link_key="label")
        grades = _rows(conn, """
            SELECT COALESCE(CAST(ci.grade AS TEXT), 'Unspecified') AS label, SUM(ci.quantity) AS quantity
            FROM collection_items ci WHERE ci.user_id = ? AND ci.ownership_type = 'Graded' AND ci.quantity > 0
            GROUP BY ci.grade ORDER BY ci.grade DESC
        """, link_key="label")
        storage = _rows(conn, """
            SELECT COALESCE(NULLIF(ci.storage_location, ''), 'Unassigned') AS label, SUM(ci.quantity) AS quantity
            FROM collection_items ci WHERE ci.user_id = ? AND ci.quantity > 0 GROUP BY label ORDER BY quantity DESC, label
        """, link_key="label")
        wishlist = _rows(conn, """
            SELECT priority AS label, COUNT(*) AS quantity FROM wishlist_items WHERE user_id = ?
            GROUP BY priority ORDER BY CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END
        """, link_key="label", link_filters={"wishlist": "1", "wishlist_priority": ""})
        for row in wishlist:
            row["link"] = _link(wishlist="1", wishlist_priority=row["label"])
        trade_summary = dict(conn.execute("""
            SELECT COUNT(DISTINCT card_id) AS cards, COALESCE(SUM(quantity), 0) AS copies,
                   COALESCE(SUM(CASE WHEN ownership_type = 'Graded' THEN quantity ELSE 0 END), 0) AS graded_copies
            FROM collection_items WHERE user_id = ? AND is_trade = 1 AND quantity > 0
        """, (DEFAULT_USER_ID,)).fetchone())
        set_progress_sql = """
            SELECT s.id, s.name AS label, COUNT(c.id) AS total_cards,
                   COUNT(DISTINCT CASE WHEN ci.quantity > 0 THEN c.id END) AS owned_cards,
                   ROUND(100.0 * COUNT(DISTINCT CASE WHEN ci.quantity > 0 THEN c.id END) / COUNT(c.id)) AS percent
            FROM sets s JOIN cards c ON c.set_id = s.id
            LEFT JOIN collection_items ci ON ci.card_id = c.id AND ci.user_id = ?
            GROUP BY s.id, s.name HAVING owned_cards > 0
        """
        most_complete = _rows(conn, f"{set_progress_sql} ORDER BY percent DESC, owned_cards DESC, label LIMIT 10")
        least_complete = _rows(conn, f"{set_progress_sql} ORDER BY percent ASC, owned_cards ASC, label LIMIT 10")
        for row in most_complete + least_complete:
            row["link"] = f"/sets/{row['id']}"
        duplicates = _rows(conn, """
            SELECT c.id AS card_id, c.name, c.number, c.image_small, s.name AS set_name, SUM(ci.quantity) AS quantity
            FROM collection_items ci JOIN cards c ON c.id = ci.card_id JOIN sets s ON s.id = c.set_id
            WHERE ci.user_id = ? AND ci.quantity > 0 GROUP BY c.id, c.name, c.number, c.image_small, s.name
            HAVING SUM(ci.quantity) > 1 ORDER BY quantity DESC, c.name COLLATE NOCASE, c.number LIMIT 20
        """)
        growth = _rows(conn, """
            SELECT substr(acquisition_date, 1, 7) AS label, SUM(quantity) AS quantity
            FROM collection_items WHERE user_id = ? AND quantity > 0 AND acquisition_date GLOB '????-??-??'
            GROUP BY substr(acquisition_date, 1, 7) ORDER BY label
        """)
        value_by_set = _rows(conn, """
            SELECT s.name AS label, COALESCE(SUM(ci.purchase_price * ci.quantity), 0) AS purchase_cost,
                   COALESCE(SUM(ci.estimated_value * ci.quantity), 0) AS estimated_value,
                   COALESCE(SUM((ci.estimated_value - ci.purchase_price) * ci.quantity), 0) AS gain
            FROM collection_items ci JOIN cards c ON c.id = ci.card_id JOIN sets s ON s.id = c.set_id
            WHERE ci.user_id = ? AND ci.quantity > 0 GROUP BY s.id, s.name HAVING estimated_value > 0
            ORDER BY estimated_value DESC, label LIMIT 20
        """, link_key="label")
        value_by_series = _rows(conn, """
            SELECT COALESCE(se.name, 'Unknown') AS label, COALESCE(SUM(ci.purchase_price * ci.quantity), 0) AS purchase_cost,
                   COALESCE(SUM(ci.estimated_value * ci.quantity), 0) AS estimated_value,
                   COALESCE(SUM((ci.estimated_value - ci.purchase_price) * ci.quantity), 0) AS gain
            FROM collection_items ci JOIN cards c ON c.id = ci.card_id JOIN sets s ON s.id = c.set_id
            LEFT JOIN series se ON se.id = s.series_id
            WHERE ci.user_id = ? AND ci.quantity > 0 GROUP BY se.id, se.name HAVING estimated_value > 0
            ORDER BY estimated_value DESC, label LIMIT 20
        """, link_key="label")
        most_valuable = _rows(conn, """
            SELECT c.id AS card_id, c.name, c.number, s.name AS set_name, SUM(ci.quantity) AS quantity,
                   SUM(ci.estimated_value * ci.quantity) AS estimated_value
            FROM collection_items ci JOIN cards c ON c.id = ci.card_id JOIN sets s ON s.id = c.set_id
            WHERE ci.user_id = ? AND ci.quantity > 0 AND ci.estimated_value IS NOT NULL
            GROUP BY c.id, c.name, c.number, s.name ORDER BY estimated_value DESC, c.name LIMIT 20
        """)
        roi_cards = _rows(conn, """
            SELECT c.id AS card_id, c.name, c.number, s.name AS set_name,
                   SUM(ci.purchase_price * ci.quantity) AS purchase_cost,
                   SUM(ci.estimated_value * ci.quantity) AS estimated_value,
                   ROUND(100.0 * (SUM(ci.estimated_value * ci.quantity) - SUM(ci.purchase_price * ci.quantity)) / SUM(ci.purchase_price * ci.quantity), 1) AS roi
            FROM collection_items ci JOIN cards c ON c.id = ci.card_id JOIN sets s ON s.id = c.set_id
            WHERE ci.user_id = ? AND ci.quantity > 0 AND ci.purchase_price IS NOT NULL AND ci.estimated_value IS NOT NULL
            GROUP BY c.id, c.name, c.number, s.name HAVING purchase_cost > 0
            ORDER BY roi DESC, estimated_value DESC LIMIT 20
        """)
    finally:
        conn.close()
    return render_template(
        "analytics.html", title="Collection Analytics", series=series, sets=sets, types=types,
        rarity=rarity, stage=stage, condition=condition, grades=grades, storage=storage,
        wishlist=wishlist, trade_summary=trade_summary, most_complete=most_complete,
        least_complete=least_complete, duplicates=duplicates, growth=growth,
        value_by_set=value_by_set, value_by_series=value_by_series, most_valuable=most_valuable, roi_cards=roi_cards,
    )
