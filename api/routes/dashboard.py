import sqlite3

from flask import Blueprint, render_template

from config import DATABASE
from models.collection import DEFAULT_USER_ID


dashboard = Blueprint("dashboard", __name__)


@dashboard.route("/")
def home():
    conn = sqlite3.connect(str(DATABASE))
    conn.row_factory = sqlite3.Row
    try:
        catalog = conn.execute(
            "SELECT COUNT(*) AS cards, (SELECT COUNT(*) FROM sets) AS sets, (SELECT COUNT(*) FROM series) AS series FROM cards"
        ).fetchone()
        summary = conn.execute(
            """
            SELECT
                COUNT(DISTINCT ci.card_id) AS owned_cards,
                COALESCE(SUM(ci.quantity), 0) AS total_copies,
                COALESCE(SUM(ci.purchase_price * ci.quantity), 0) AS total_spent,
                COUNT(DISTINCT c.set_id) AS started_sets
            FROM collection_items ci
            JOIN cards c ON c.id = ci.card_id
            WHERE ci.user_id = ? AND ci.quantity > 0
            """,
            (DEFAULT_USER_ID,),
        ).fetchone()
        recent_items = conn.execute(
            """
            SELECT ci.id, ci.quantity, ci.variant, ci.ownership_type, ci.updated_at,
                   c.id AS card_id, c.name, c.number, c.image_small, s.id AS set_id, s.name AS set_name
            FROM collection_items ci
            JOIN cards c ON c.id = ci.card_id
            JOIN sets s ON s.id = c.set_id
            WHERE ci.user_id = ? AND ci.quantity > 0
            ORDER BY ci.updated_at DESC, ci.id DESC
            LIMIT 6
            """,
            (DEFAULT_USER_ID,),
        ).fetchall()
        set_rows = conn.execute(
            """
            SELECT s.id, s.name, s.logo, s.symbol, s.release_date, s.printed_total,
                   COUNT(c.id) AS card_total,
                   COUNT(DISTINCT CASE WHEN ci.quantity > 0 THEN c.id END) AS owned_cards
            FROM sets s
            LEFT JOIN cards c ON c.set_id = s.id
            LEFT JOIN collection_items ci ON ci.card_id = c.id AND ci.user_id = ?
            GROUP BY s.id, s.name, s.logo, s.symbol, s.release_date, s.printed_total
            HAVING COUNT(DISTINCT CASE WHEN ci.quantity > 0 THEN c.id END) > 0
            ORDER BY CAST(COUNT(DISTINCT CASE WHEN ci.quantity > 0 THEN c.id END) AS REAL) / NULLIF(COUNT(c.id), 0) DESC,
                     s.release_date DESC, s.name COLLATE NOCASE
            LIMIT 6
            """,
            (DEFAULT_USER_ID,),
        ).fetchall()
    finally:
        conn.close()

    total_cards = catalog["cards"]
    owned_cards = summary["owned_cards"]
    progress = round((owned_cards / total_cards) * 100) if total_cards else 0
    set_progress = []
    for set_row in set_rows:
        item = dict(set_row)
        item["percent_complete"] = round((item["owned_cards"] / item["card_total"]) * 100) if item["card_total"] else 0
        set_progress.append(item)
    return render_template(
        "home.html",
        title="Collector Dashboard",
        series=catalog["series"],
        sets=catalog["sets"],
        cards=total_cards,
        owned_cards=owned_cards,
        total_copies=summary["total_copies"],
        total_spent=summary["total_spent"],
        started_sets=summary["started_sets"],
        progress=progress,
        recent_items=recent_items,
        set_progress=set_progress,
    )
