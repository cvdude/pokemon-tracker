from flask import Blueprint, render_template
import sqlite3

from config import DATABASE
from models.collection import DEFAULT_USER_ID


collection = Blueprint("collection", __name__)


@collection.route("/collection")
def collection_page():
    conn = sqlite3.connect(str(DATABASE))
    conn.row_factory = sqlite3.Row
    try:
        cards = conn.execute(
            """
            SELECT
                ci.id,
                ci.quantity,
                ci.condition,
                ci.variant,
                ci.storage_location,
                ci.acquisition_date,
                ci.purchase_price,
                ci.notes,
                ci.is_favorite,
                c.id AS card_id,
                c.name,
                c.number,
                c.image_small,
                c.image_large,
                c.rarity,
                c.hp,
                c.category,
                c.artist,
                s.name AS set_name
            FROM collection_items ci
            JOIN cards c ON c.id = ci.card_id
            JOIN sets s ON s.id = c.set_id
            WHERE ci.user_id = ?
            ORDER BY c.name COLLATE NOCASE, c.number, ci.id
            """,
            (DEFAULT_USER_ID,),
        ).fetchall()
    finally:
        conn.close()

    total_cards = len({card["card_id"] for card in cards})
    total_quantity = sum(card["quantity"] for card in cards)
    return render_template(
        "collection.html",
        title="My Collection",
        cards=cards,
        total_cards=total_cards,
        total_quantity=total_quantity,
    )
