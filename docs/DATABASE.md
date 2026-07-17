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
| `collection_items` | Active ownership table. `user_id` references `users.id`; `card_id` references `cards.id`. It stores raw/graded ownership type, condition, variant and custom variant, language, grading company and custom company, grade, certification number, storage, acquisition, price, notes, and timestamps. Each row is an independent owned entry. |

## Catalog versus collection

Catalog tables describe what a Pokémon card *is*: its set, number, name, printed attributes, images, attacks, and related metadata. They are shared reference records and must not be changed when a user acquires a card.

Collection tables describe what a user *owns*. `collection_items` records each owned grouping and its personal metadata. Catalog progress is derived from these records: a card is owned when the user has a positive summed quantity for that card.

## Runtime migration

At application startup, `ensure_collection_schema()` creates `collection_items` and the `idx_collection_items_card_user` index if needed. It then copies legacy `inventory` rows into the new table without duplicating equivalent rows. Database and backup files are intentionally retained in the repository.
