from flask import Blueprint, render_template
import sqlite3

collection = Blueprint("collection", __name__)

DATABASE = "/volume1/web/pokemon-tracker/database/pokemon.db"


@collection.route("/collection")
def collection_page():

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT
            c.name,
            c.number,
            c.image_small,
            c.image_large,
            c.rarity,
            c.hp,
            c.category,
            c.artist,
            l.name AS location,
            i.quantity,
            i.favorite
        FROM inventory i
        JOIN cards c ON i.card_id = c.id
        JOIN locations l ON i.location_id = l.id
        ORDER BY c.name
    """)

    cards = cur.fetchall()

    conn.close()

    return render_template(
        "collection.html",
        title="My Collection",
        cards=cards
    )