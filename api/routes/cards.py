@cards.route("/sets/<set_id>")
def cards_by_set(set_id):

    conn = sqlite3.connect(str(DATABASE))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Get set info
    cur.execute("""
        SELECT
            id,
            name
        FROM sets
        WHERE id = ?
    """, (set_id,))

    set_info = cur.fetchone()

    if set_info is None:
        conn.close()
        return "Set not found", 404

    # Get cards with owned count
    cur.execute("""
        SELECT
            c.id,
            c.number,
            c.name,
            c.rarity,
            c.image_small,
            c.hp,
            c.category,
            c.artist,

            COALESCE(SUM(i.quantity),0) AS owned

        FROM cards c

        LEFT JOIN inventory i
            ON c.id = i.card_id
           AND i.user_id = 1

        WHERE c.set_id = ?

        GROUP BY
            c.id,
            c.number,
            c.name,
            c.rarity,
            c.image_small,
            c.hp,
            c.category,
            c.artist

        ORDER BY
            CAST(c.number AS INTEGER),
            c.number
    """, (set_id,))

    cards_list = cur.fetchall()

    total_cards = len(cards_list)
    owned_cards = sum(1 for c in cards_list if c["owned"] > 0)
    missing_cards = total_cards - owned_cards

    percent_complete = 0
    if total_cards:
        percent_complete = round((owned_cards / total_cards) * 100)

    conn.close()

    return render_template(
        "cards.html",
        title=set_info["name"],
        set_name=set_info["name"],
        cards=cards_list,
        total_cards=total_cards,
        owned_cards=owned_cards,
        missing_cards=missing_cards,
        percent_complete=percent_complete
    )