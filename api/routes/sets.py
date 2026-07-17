from flask import Blueprint, render_template
import sqlite3
from config import DATABASE
from models.collection import DEFAULT_USER_ID

sets = Blueprint("sets", __name__)


@sets.route("/sets")
def sets_page():

    conn = sqlite3.connect(str(DATABASE))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
    SELECT
        s.id,
        s.name,
        s.release_date,
        COUNT(DISTINCT c.id) AS printed_total,
        s.logo,
        s.symbol,
        COUNT(DISTINCT CASE WHEN ci.quantity > 0 THEN c.id END) AS owned_count
    FROM sets s
    LEFT JOIN cards c
        ON s.id = c.set_id
    LEFT JOIN collection_items ci
        ON c.id = ci.card_id
        AND ci.user_id = ?
        AND ci.quantity > 0
    GROUP BY
    s.id,
    s.name,
    s.release_date,
    s.printed_total,
    s.logo,
    s.symbol

ORDER BY
    CASE
        WHEN s.release_date IS NULL THEN 1
        ELSE 0
    END,
    s.release_date ASC,
    s.name ASC;
""", (DEFAULT_USER_ID,))

    sets = cur.fetchall()

    conn.close()

    return render_template(
        "sets.html",
        title="Sets",
        sets=sets
    )
