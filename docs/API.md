# EvoDeck routes and JSON API

All current routes are registered without a URL prefix. HTML routes render Jinja templates; JSON routes return `application/json`.

## HTML routes

| Method | Route | Response |
|---|---|---|
| GET | `/` | Dashboard with series, set, and catalog-card counts. |
| GET | `/sets` | Set browser page. |
| GET | `/sets/<set_id>` | Cards in a set, including collection progress and add controls. Returns 404 when the set is absent. |
| GET | `/card/<card_id>` | Card-detail page with ability, attacks, weaknesses, resistances, retreat cost, and adjacent cards. Returns 404 when absent. |
| GET | `/collection` | Current user’s collection items and totals. |

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

Equivalent add routes. Accept JSON or form fields: `quantity` (1–1000), `condition`, `variant`, `language`, `storage_location`, `acquisition_date` (`YYYY-MM-DD`), `purchase_price`, and `notes`. `condition` is limited to the supported collection conditions; `variant` and `language` also accept `Other` with `variant_other` or `language_other`. Missing optional fields use collection defaults. Equivalent copies are merged by the collection-item unique key.

```json
{"success": true, "count": 2}
```

Invalid fields return `400` with `{"success":false,"error":"..."}`; an unknown card returns `404`.

### `POST /inventory/remove/<card_id>`

Removes one copy from the most recently updated collection item for the card, deleting that item at zero quantity.

```json
{"success": true, "count": 1}
```

### `PATCH /collection/items/<item_id>`

Updates one collection item. Accepts the same fields as add; `quantity` is optional for a partial update.

```json
{"success": true, "count": 3}
```

Returns `400` for invalid data, `404` for an item outside the current user’s collection, and `409` if the updated fields duplicate another collection item.
