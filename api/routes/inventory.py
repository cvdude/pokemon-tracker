from flask import Blueprint, jsonify
import sqlite3

from config import DATABASE

inventory = Blueprint("inventory", __name__)


def get_connection():
    conn = sqlite3.connect(str(DATABASE))
    conn.row_factory = sqlite3.Row
    return conn


def get_count(cur, card_id):
    cur.execute("""
        SELECT COALESCE(SUM(quantity),0)
        FROM inventory
        WHERE user_id = 1
          AND card_id = ?
    """, (card_id,))

    return cur.fetchone()[0]


@inventory.route("/inventory/count/<card_id>")
def inventory_count(card_id):

    conn = get_connection()
    cur = conn.cursor()

    count = get_count(cur, card_id)

    conn.close()

    return jsonify({
        "count": count
    })


@inventory.route("/inventory/add/<card_id>", methods=["POST"])
def add_card(card_id):

    conn = get_connection()
    cur = conn.cursor()

    #
    # Look for existing normal copy
    #
    cur.execute("""
        SELECT
            id,
            quantity
        FROM inventory
        WHERE
            user_id = 1
            AND card_id = ?
            AND variant_id IS NULL
            AND location_id = 1
            AND condition_id IS NULL
    """, (card_id,))

    row = cur.fetchone()

    if row:

        cur.execute("""
            UPDATE inventory
            SET
                quantity = quantity + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (row["id"],))

    else:

        cur.execute("""
            INSERT INTO inventory
            (
                user_id,
                card_id,
                variant_id,
                location_id,
                condition_id,
                quantity
            )
            VALUES
            (
                1,
                ?,
                NULL,
                1,
                NULL,
                1
            )
        """, (card_id,))

    conn.commit()

    count = get_count(cur, card_id)

    conn.close()

    return jsonify({
        "success": True,
        "count": count
    })


@inventory.route("/inventory/remove/<card_id>", methods=["POST"])
def remove_card(card_id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            id,
            quantity
        FROM inventory
        WHERE
            user_id = 1
            AND card_id = ?
            AND variant_id IS NULL
            AND location_id = 1
            AND condition_id IS NULL
    """, (card_id,))

    row = cur.fetchone()

    if row:

        if row["quantity"] > 1:

            cur.execute("""
                UPDATE inventory
                SET
                    quantity = quantity - 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (row["id"],))

        else:

            cur.execute("""
                DELETE
                FROM inventory
                WHERE id = ?
            """, (row["id"],))

    conn.commit()

    count = get_count(cur, card_id)

    conn.close()

    return jsonify({
        "success": True,
        "count": count
    })