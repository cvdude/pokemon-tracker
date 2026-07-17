# EvoDeck architecture

EvoDeck is a server-rendered Pokémon Trading Card application built with Flask, SQLite, Jinja templates, CSS, and browser JavaScript. The Flask entry point is `api/app.py`; it creates the application, initializes the collection schema, and registers the route blueprints.

## Application layout

- `api/app.py` — application startup, safe schema migrations, shared preference context, display filters, JSON error handling, and blueprint registration.
- `api/config.py` — resolves the repository-local SQLite database at `database/pokemon.db`.
- `api/models/` — database-focused code. `models/collection.py` creates and migrates ownership, wishlist, and backup tables; `models/settings.py` manages extensible JSON-backed preferences.
- `api/routes/` — Flask blueprints for dashboard, catalog/card detail, sets, collection search, inventory/wishlist mutations, analytics, backups, and settings.
- `api/services/` — domain helpers for Master Set progress and forward-compatible backup/import processing.
- `api/templates/` — Jinja pages and reusable components. `layout.html` is the shared shell and `components/card_tile.html` renders a catalog card with collection controls.
- `api/static/` — browser assets. Collection, wishlist, analytics, backup, preferences, settings, and image-viewer modules are loaded only where needed; `static/css/style.css` contains shared responsive and theme styles.

## Request flow

1. A blueprint route opens a SQLite connection using `config.DATABASE`.
2. Catalog routes read `cards`, `sets`, and card-detail tables.
3. Collection mutations write to `collection_items`; catalog data is never updated to record ownership.
4. The route returns either a Jinja-rendered page or a JSON response.
5. Browser modules call JSON mutation routes, surface loading/errors in their dialogs, and refresh state only after a successful change.

## Data import and synchronization

- `importers/` contains the repository’s local import pipeline: parser, mapping, repository client, database helper, rebuild script, and card/set/series import and sync scripts.
- `sync/` contains an alternate/deployment-oriented synchronization toolkit, including remote download, table creation, metadata and card synchronization, record counts, and auditing.
- `database/schema_v0.sql` is the baseline schema. `models/collection.py` also uses idempotent runtime schema creation so existing databases gain `collection_items` safely.

## Ownership model

The catalog (`cards`, `sets`, and related metadata) is shared reference data. A user’s copies belong in `collection_items`. Card pages calculate `owned` by summing collection-item quantities for the current default user (`user_id = 1`), so collection changes update progress without changing catalog rows.
