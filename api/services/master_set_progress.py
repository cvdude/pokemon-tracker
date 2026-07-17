"""Master Set progress derived from catalog variants and owned collection items."""


def _has_source_variant_ids(connection):
    """Return whether this database has imported, addressable variant records."""
    columns = {
        row[1] for row in connection.execute("PRAGMA table_info(variants)").fetchall()
    }
    return "source_variant_id" in columns


def get_set_master_progress(connection, set_id, user_id):
    """Calculate Master Set completion without changing catalog or collection data.

    An imported variant is one Master Set requirement.  A catalog card with no
    imported variants remains one requirement, so the metric remains useful
    until its source data supplies card-specific printings.  Older collection
    rows that predate ``source_variant_id`` are matched by their saved variant
    name where possible.
    """
    card_total = connection.execute(
        "SELECT COUNT(*) FROM cards WHERE set_id = ?", (set_id,)
    ).fetchone()[0]

    if not _has_source_variant_ids(connection):
        owned = connection.execute(
            """
            SELECT COUNT(*)
            FROM cards c
            WHERE c.set_id = ?
              AND EXISTS (
                  SELECT 1 FROM collection_items ci
                  WHERE ci.card_id = c.id AND ci.user_id = ? AND ci.quantity > 0
              )
            """,
            (set_id, user_id),
        ).fetchone()[0]
        return _progress(card_total, owned, 0, card_total)

    imported_total = connection.execute(
        """
        SELECT COUNT(*)
        FROM variants v
        JOIN cards c ON c.id = v.card_id
        WHERE c.set_id = ?
          AND v.source_variant_id IS NOT NULL AND v.source_variant_id <> ''
        """,
        (set_id,),
    ).fetchone()[0]
    imported_owned = connection.execute(
        """
        SELECT COUNT(*)
        FROM variants v
        JOIN cards c ON c.id = v.card_id
        WHERE c.set_id = ?
          AND v.source_variant_id IS NOT NULL AND v.source_variant_id <> ''
          AND EXISTS (
              SELECT 1
              FROM collection_items ci
              WHERE ci.card_id = v.card_id
                AND ci.user_id = ?
                AND ci.quantity > 0
                AND (
                    ci.source_variant_id = v.source_variant_id
                    OR (
                        (ci.source_variant_id IS NULL OR ci.source_variant_id = '')
                        AND LOWER(TRIM(COALESCE(ci.custom_variant, ci.variant))) = LOWER(TRIM(v.name))
                    )
                )
          )
        """,
        (set_id, user_id),
    ).fetchone()[0]
    fallback_total = connection.execute(
        """
        SELECT COUNT(*)
        FROM cards c
        WHERE c.set_id = ?
          AND NOT EXISTS (
              SELECT 1 FROM variants v
              WHERE v.card_id = c.id
                AND v.source_variant_id IS NOT NULL AND v.source_variant_id <> ''
          )
        """,
        (set_id,),
    ).fetchone()[0]
    fallback_owned = connection.execute(
        """
        SELECT COUNT(*)
        FROM cards c
        WHERE c.set_id = ?
          AND NOT EXISTS (
              SELECT 1 FROM variants v
              WHERE v.card_id = c.id
                AND v.source_variant_id IS NOT NULL AND v.source_variant_id <> ''
          )
          AND EXISTS (
              SELECT 1 FROM collection_items ci
              WHERE ci.card_id = c.id AND ci.user_id = ? AND ci.quantity > 0
          )
        """,
        (set_id, user_id),
    ).fetchone()[0]
    return _progress(
        imported_total + fallback_total,
        imported_owned + fallback_owned,
        imported_total,
        fallback_total,
    )


def _progress(total, owned, imported_total, fallback_total):
    return {
        "total": total,
        "owned": owned,
        "missing": total - owned,
        "percent_complete": round((owned / total) * 100) if total else 0,
        "imported_variant_total": imported_total,
        "fallback_card_total": fallback_total,
    }
