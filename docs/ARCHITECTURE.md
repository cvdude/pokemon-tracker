# EvoDeck architecture

EvoDeck is a server-rendered Pokémon Trading Card application built with Flask, SQLite, Jinja templates, CSS, and browser JavaScript. The Flask entry point is `api/app.py`; it creates the application, initializes the collection schema, and registers the route blueprints.

## Application layout

- `api/app.py` — application startup and blueprint registration.
- `api/config.py` — resolves the repository-local SQLite database at `database/pokemon.db`.
- `api/models/` — database-focused code. `models/collection.py` creates and migrates the collection ownership table at application startup.
- `api/routes/` — Flask blueprints for the dashboard, sets, cards, collection, and collection mutation endpoints. `admin.py` and `catalog.py` are placeholders.
- `api/services/` — integrations and domain helpers for TCGdex metadata, pricing, and variants.
- `api/templates/` — Jinja pages and reusable components. `layout.html` is the shared shell and `components/card_tile.html` renders a catalog card with collection controls.
- `api/static/` — browser assets. `static/js/inventory.js` powers the add/remove and detailed-add controls; `static/css/` contains the site styles.

## Request flow

1. A blueprint route opens a SQLite connection using `config.DATABASE`.
2. Catalog routes read `cards`, `sets`, and card-detail tables.
3. Collection mutations write to `collection_items`; catalog data is never updated to record ownership.
4. The route returns either a Jinja-rendered page or a JSON response.
5. The cards page JavaScript calls the collection mutation routes and refreshes its display when necessary.

## Data import and synchronization

- `importers/` contains the repository’s local import pipeline: parser, mapping, repository client, database helper, rebuild script, and card/set/series import and sync scripts.
- `sync/` contains an alternate/deployment-oriented synchronization toolkit, including remote download, table creation, metadata and card synchronization, record counts, and auditing.
- `database/schema_v0.sql` is the baseline schema. `models/collection.py` also uses idempotent runtime schema creation so existing databases gain `collection_items` safely.

## Ownership model

The catalog (`cards`, `sets`, and related metadata) is shared reference data. A user’s copies belong in `collection_items`. Card pages calculate `owned` by summing collection-item quantities for the current default user (`user_id = 1`), so collection changes update progress without changing catalog rows.
