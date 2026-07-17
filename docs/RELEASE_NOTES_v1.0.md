# EvoDeck 1.0 Release Notes

## Collector experience

- Collector dashboard with collection, Master Set, wishlist, trade, duplicate, purchase, and valuation summaries.
- Advanced catalog and collection search with persistent URL filters and sortable results.
- Set pages, complete card-detail workspaces, Master Set progress, and card-specific imported variants.
- Full ownership tracking for separate raw or graded copies, quantities, conditions, locations, purchase and valuation details, notes, duplication, moves, edits, deletes, and trade flags.
- Wishlist entries for cards or specific imported variants, including priority, desired condition, target price, and notes.

## Analysis and presentation

- Aggregate SQL analytics for collection composition, storage, condition, grading, growth, value, ROI, completion, and duplicates.
- User settings for theme, card size, collection defaults, date/currency display, and dashboard widget layout.
- Responsive high-resolution card viewer with pan, zoom, scan switching, previous/next navigation, and variant ownership comparison.

## Data safety and operations

- Idempotent normalized TCGdex variant importer and audit tooling.
- Versioned JSON and CSV exports for collection, inventory, wishlist, trade, purchase, and valuation data.
- Import previews, duplicate detection, merge/replace modes, transactions, automatic SQLite snapshots, backup history, and restore.
- Safe startup migrations that preserve catalog and collection records.

## RC1 quality pass

- Removed confirmed unused zero-byte placeholders and stale duplicate requirement file.
- Repaired Catalog navigation and aligned set ownership counts with `collection_items`.
- Added a wishlist lookup index and standardized JSON HTTP errors.
- Improved interactive loading, error feedback, submit states, and modal accessibility.

## Deployment

EvoDeck runs with Flask and SQLite, and includes a Python 3.9 Gunicorn container configuration for Synology Container Manager. The live SQLite database remains in the mounted `database/` directory across container rebuilds.
