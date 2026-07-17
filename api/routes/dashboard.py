import sqlite3

from flask import Blueprint, render_template

from config import DATABASE
from models.collection import DEFAULT_USER_ID
from services.master_set_progress import get_master_collection_summary


dashboard = Blueprint("dashboard", __name__)


@dashboard.route("/")
def home():
    conn = sqlite3.connect(str(DATABASE))
    conn.row_factory = sqlite3.Row
    try:
        catalog = conn.execute(
            "SELECT COUNT(*) AS cards, (SELECT COUNT(*) FROM sets) AS sets, (SELECT COUNT(*) FROM series) AS series FROM cards"
        ).fetchone()
        collection = conn.execute(
            """
            SELECT COUNT(DISTINCT ci.card_id) AS owned_cards,
                   COALESCE(SUM(ci.quantity), 0) AS total_copies,
                   COUNT(DISTINCT c.set_id) AS started_sets
            FROM collection_items ci JOIN cards c ON c.id = ci.card_id
            WHERE ci.user_id = ? AND ci.quantity > 0
            """,
            (DEFAULT_USER_ID,),
        ).fetchone()
        master = get_master_collection_summary(conn, DEFAULT_USER_ID)
        recent_cards = conn.execute(
            """
            SELECT ci.id, ci.quantity, ci.variant, ci.updated_at, c.id AS card_id,
                   c.name, c.number, c.image_small, s.id AS set_id, s.name AS set_name
            FROM collection_items ci JOIN cards c ON c.id = ci.card_id
            JOIN sets s ON s.id = c.set_id
            WHERE ci.user_id = ? AND ci.quantity > 0
            ORDER BY ci.updated_at DESC, ci.id DESC LIMIT 10
            """,
            (DEFAULT_USER_ID,),
        ).fetchall()
        duplicate_cards = conn.execute(
            """
            SELECT c.id AS card_id, c.name, c.number, c.image_small, s.name AS set_name,
                   SUM(ci.quantity) AS quantity
            FROM collection_items ci JOIN cards c ON c.id = ci.card_id
            JOIN sets s ON s.id = c.set_id
            WHERE ci.user_id = ? AND ci.quantity > 0
            GROUP BY c.id, c.name, c.number, c.image_small, s.name
            HAVING SUM(ci.quantity) > 1
            ORDER BY quantity DESC, c.name COLLATE NOCASE, c.number
            LIMIT 10
            """,
            (DEFAULT_USER_ID,),
        ).fetchall()
        set_rows = conn.execute(
            """
            SELECT s.id, s.name, s.logo, s.printed_total, COUNT(c.id) AS card_total,
                   COUNT(DISTINCT CASE WHEN ci.quantity > 0 THEN c.id END) AS owned_cards
            FROM sets s LEFT JOIN cards c ON c.set_id = s.id
            LEFT JOIN collection_items ci ON ci.card_id = c.id AND ci.user_id = ?
            GROUP BY s.id, s.name, s.logo, s.printed_total
            HAVING COUNT(DISTINCT CASE WHEN ci.quantity > 0 THEN c.id END) > 0
            ORDER BY CAST(COUNT(DISTINCT CASE WHEN ci.quantity > 0 THEN c.id END) AS REAL) / NULLIF(COUNT(c.id), 0) DESC,
                     COUNT(DISTINCT CASE WHEN ci.quantity > 0 THEN c.id END) DESC, s.name COLLATE NOCASE
            LIMIT 10
            """,
            (DEFAULT_USER_ID,),
        ).fetchall()
    finally:
        conn.close()

    total_cards = catalog["cards"]
    owned_cards = collection["owned_cards"]
    missing_cards = total_cards - owned_cards
    completion = round((owned_cards / total_cards) * 100) if total_cards else 0
    top_sets = []
    for row in set_rows:
        item = dict(row)
        item["percent_complete"] = round((item["owned_cards"] / item["card_total"]) * 100) if item["card_total"] else 0
        top_sets.append(item)
    return render_template(
        "home.html", title="Collector Dashboard", series=catalog["series"], sets=catalog["sets"], cards=total_cards,
        owned_cards=owned_cards, total_copies=collection["total_copies"], started_sets=collection["started_sets"],
        missing_cards=missing_cards, completion=completion, master=master, recent_cards=recent_cards,
        duplicate_cards=duplicate_cards, top_sets=top_sets,
    )
