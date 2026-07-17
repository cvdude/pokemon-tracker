# EvoDeck database

The application uses SQLite at `database/pokemon.db`. Foreign keys describe the intended model; application queries use the relationships listed below.

## Catalog tables

| Table | Purpose and relationships |
|---|---|
| `metadata` | Key/value application metadata. |
| `series` | Pokémon card series. One `series` has many `sets`. |
| `sets` | Set metadata, including release date and image references. `series_id` references `series.id`; one set has many `cards`. |
| `cards` | The immutable card catalog. `set_id` references `sets.id`; one card has many related detail records and collection items. |
| `variants` | Normalized imported variant definitions. `card_id` references `cards.id`; `source_variant_id` is the stable source key, while `name`, `variant_type`, `finish`, and `edition` provide display and printing metadata. |

`importers/audit_variants.py` audits only the verified TCGdex `variants` formats: legacy arrays of `{ type: "..." }` and modern boolean objects. Rarity, suffix, edition, stamp, and finish are not independent variant sources.
| `card_images` | Optional image references for one card. `card_id` is both the primary key and a reference to `cards.id`. |
| `card_types` | Repeating card type values. `card_id` references `cards.id`. |
| `card_subtypes` | Repeating subtype values. `card_id` references `cards.id`. |
| `abilities` | Card abilities. `card_id` references `cards.id`. |
| `attacks` | Card attacks. `card_id` references `cards.id`; one attack has many `attack_cost` rows. |
| `attack_cost` | Energy costs for an attack. `attack_id` references `attacks.id`. |
| `weaknesses` | Card weaknesses. `card_id` references `cards.id`. |
| `resistances` | Card resistances. `card_id` references `cards.id`. |
| `retreat_cost` | Repeating retreat-energy values. `card_id` references `cards.id`. |

## Collection and user tables

| Table | Purpose and relationships |
|---|---|
| `users` | Application users. The current UI uses the default user, ID `1`. |
| `locations` | Legacy named storage locations. |
| `inventory` | Legacy per-user inventory records. It links `user_id` to `users`, `card_id` to `cards`, and `location_id` to `locations`; it remains for backward compatibility and is migrated into `collection_items` at startup. |
| `collection` | Legacy variant-based collection table. `variant_id` references `variants.id`. It is retained in the baseline schema but is not the active ownership engine. |
| `collection_items` | Active ownership table. `user_id` references `users.id`; `card_id` references `cards.id`. It stores raw/graded ownership type, condition, variant and custom variant, language, grading company and custom company, grade, certification number, storage, acquisition, price, notes, timestamps, and `is_trade`. It also stores purchase date/source, per-copy purchase price, estimated and previous estimated value, valuation date/source, insurance value, and ISO currency. Each row is an independent owned entry. |
| `wishlist_items` | User wishlist entries. `user_id` references `users.id`; `card_id` references `cards.id`; nullable `source_variant_id` identifies a specific desired imported variant. It stores priority, desired condition, target price, notes, and timestamps. One user may have one card-level and one row per source variant for the same card. |
| `backup_history` | Metadata for application-created SQLite snapshots. `filename` identifies a file in `backups/`; `operation`, `created_at`, `file_size`, and `notes` provide a restorable audit history. The snapshot itself remains a full database backup. |

## Catalog versus collection

Catalog tables describe what a Pokémon card *is*: its set, number, name, printed attributes, images, attacks, and related metadata. They are shared reference records and must not be changed when a user acquires a card.

Collection tables describe what a user *owns*. `collection_items` records each owned grouping and its personal metadata. Catalog progress is derived from these records: a card is owned when the user has a positive summed quantity for that card.

`wishlist_items` describes cards or specific imported variants a user wants; it does not change catalog or ownership progress. `collection_items.is_trade` marks an owned copy as available to trade without changing its quantity or completion state.

Valuation fields belong to `collection_items`, never to catalog cards. `previous_estimated_value`, `last_valuation_date`, `valuation_source`, and `currency` retain enough context for future TCGplayer, Cardmarket, eBay, or other pricing integrations to update per-copy values without changing the schema.

## Master Set progress

Master Set progress is calculated at read time; it adds no ownership or catalog records. Each imported `variants.source_variant_id` row is a required printing for its card. A card without imported variant rows counts as one fallback requirement until source data is available. An imported requirement is owned when a positive-quantity `collection_items` row has the matching `source_variant_id`; legacy entries without that identifier are matched by their saved human-readable variant name. This is separate from standard collection progress, which counts one owned catalog card regardless of its printing.

## Runtime migration

At application startup, `ensure_collection_schema()` safely creates or extends `collection_items`, creates `wishlist_items`, `backup_history`, and their indexes without modifying catalog records. It then copies legacy `inventory` rows into the new table without duplicating equivalent rows.

## Backup and import data

Backups are complete SQLite snapshots stored in `backups/`; an automatic snapshot is made before every import and before every restore. The `backup_history` table tracks only snapshots made by EvoDeck. JSON exports use the versioned `evodeck-collection-export` envelope and include only collection and wishlist data, so importing cannot replace catalog tables. CSV exports flatten the same records for spreadsheet use. Imports reject future format versions, validate referenced catalog card IDs, and run all data changes in one transaction; a failed import is rolled back.
