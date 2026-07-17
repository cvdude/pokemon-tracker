# EvoDeck routes and JSON API

All current routes are registered without a URL prefix. HTML routes render Jinja templates; JSON routes return `application/json`.

## HTML routes

| Method | Route | Response |
|---|---|---|
| GET | `/` | Dashboard with series, set, and catalog-card counts. |
| GET | `/analytics` | Aggregate collection analytics with linked Chart.js breakdowns, set-completion lists, duplicates, trade, wishlist, and monthly growth. |
| GET | `/sets` | Set browser page. |
| GET | `/sets/<set_id>` | Cards in a set, including collection progress and add controls. Returns 404 when the set is absent. |
| GET | `/card/<card_id>` | Card-detail page with ability, attacks, weaknesses, resistances, retreat cost, and adjacent cards. Returns 404 when absent. |
| GET | `/collection` | Advanced collection and catalog search. Supports `q`, `ownership` (`owned`, `missing`, or `all`), `duplicates`, `grading`, `master`, `has_notes`, `sort`, and `order`; filter state is retained in the URL. |

## Card API

### `GET /api/cards`

Returns a paginated catalog result.

Optional query parameters: `page`, `per_page` (or `limit`), `sort`, `order`, `set_id`, `series_id`, `category`, `rarity`, `owned`, and search terms `q`, `query`, or `search`. `owned` accepts `true`/`false`, `yes`/`no`, or `1`/`0`.

```json
{
  "cards": [{"id": "...", "name": "...", "owned": 0}],
  "pagination": {"page": 1, "per_page": 24, "total": 0, "total_pages": 0, "has_next": false, "has_previous": false},
  "sort": "number",
  "order": "asc"
}
```

### `GET /api/cards/search`

Same response and filters as `/api/cards`; defaults to sorting by `name`.

### `GET /api/cards/random`

Returns one random card after applying supported filters.

```json
{"card": {"id": "...", "name": "...", "owned": 0}}
```

Returns `404` with `{"error":"No cards found"}` if no card matches.

### `GET /api/cards/recent`

Same paginated response as `/api/cards`, ordered by newest non-null `updated_at`, then card ID.

### `GET /api/cards/<card_id>`

Returns one card plus related detail arrays.

```json
{
  "card": {
    "id": "...",
    "name": "...",
    "owned": 0,
    "abilities": [],
    "attacks": [],
    "weaknesses": [],
    "resistances": [],
    "retreat_cost": []
  }
}
```

Returns `404` with `{"error":"Card not found"}` when absent.

## Collection JSON routes

### `GET /inventory/count/<card_id>`

Returns the current user’s summed collection quantity for a card.

```json
{"count": 2}
```

### `POST /inventory/add/<card_id>` and `POST /collection/items/<card_id>`

Equivalent add routes accept raw or graded ownership metadata. Graded items require `grading_company` and a decimal `grade`; raw items use the supported condition set. Each request creates an independent collection entry.

```json
{"success": true, "count": 2}
```

Invalid fields return `400` with `{"success":false,"error":"..."}`; an unknown card returns `404`.

### `POST /inventory/remove/<card_id>`

Removes one copy from the most recently updated collection item for the card, deleting that item at zero quantity.

```json
{"success": true, "count": 1}
```

### `GET /collection/items/card/<card_id>`

Returns every separate collection entry owned for the card, newest first.

```json
{"items": [{"id": 12, "quantity": 1, "condition": "Near Mint", "variant": "Normal", "language": "English"}]}
```

### `GET /wishlist/items/card/<card_id>`

Returns the current user's card-level and source-variant-specific wishlist entries for a card.

### `POST /wishlist/items/<card_id>`

Creates or updates a wishlist entry. Optional `source_variant_id` targets one imported variant. Accepted fields are `priority` (`Low`, `Medium`, or `High`), `desired_condition`, `target_price`, and `notes`.

### `PATCH` / `DELETE /wishlist/items/<item_id>`

Updates or removes one current-user wishlist entry. PATCH accepts the same editable wishlist fields as POST.

### `PATCH /collection/items/<item_id>`

Updates one collection item. Accepts the same fields as add; `quantity` is optional for a partial update.

```json
{"success": true, "count": 3}
```

Returns `400` for invalid data and `404` for an item outside the current user’s collection.

### `DELETE /collection/items/<item_id>`

Deletes exactly one collection entry and returns the remaining card quantity: `{"success":true,"count":1}`. Returns `404` when the entry is absent.

### `PATCH /collection/items/<item_id>/trade`

Sets an owned collection item's trade-list flag. Send `{"is_trade": true}` to make a copy available for trade or `false` to remove it from the trade list.

### `POST /collection/items/<item_id>/duplicate`

Creates a separate copy of one collection entry, preserving its metadata and quantity. Returns `201` with `{"success":true,"item_id":13,"count":2}`.
