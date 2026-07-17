# Changelog

## Initial project

Established the EvoDeck Flask application, SQLite catalog, templates, import tooling, and synchronization scripts.

## Restore cards API routes

Restored the cards blueprint, catalog and detail API routes, pagination, search, sorting, filtering, random and recent card endpoints, and card/set pages.

## Repository cleanup

Added project ignore rules and removed generated Python cache files and server dependency artifacts from version control.

## Collection engine

Added `collection_items`, migrated legacy inventory records, introduced collection metadata and mutation endpoints, and connected ownership progress to collection data.

## Collection detail dialog

Replaced immediate add behavior with a validated add/edit modal for quantity, condition, variant, language, storage, price, date acquired, and notes. Collection ownership progress refreshes after every save.

## Complete collection item management

Added full per-card copy management: viewing all entries, independent entry creation, editing, duplication, confirmed deletion, keyboard dialog support, and accurate progress refreshes.

## Raw and graded collection tracking

Added raw and graded ownership fields, grading metadata, imported variant lookup, and a first-copy form flow.

## Card variant importer

Added an idempotent NAS importer for the TypeScript source card `variants` object and normalized variant metadata.

## Card-specific collection variants

Collection entries can now retain stable imported variant identifiers while preserving readable names and fallback custom values.

## Variant coverage audit

Added a source-to-database audit for explicit TypeScript card variant data.

## Finalize variant import pipeline

Aligned variant import and audit reporting with the verified legacy-array and modern boolean-object TCGdex formats.

## Master Set progress engine

Added read-only per-set Master Set progress based on imported card-specific variants, with a safe one-card fallback where no variant records exist. Standard collection progress remains unchanged.

## Dedicated card detail pages

Expanded the existing card detail route into a complete card workspace with card facts, types, abilities, attack costs, ownership status, and the shared collection-management dialog.

## Collector dashboard

Replaced the catalog-only landing page with collector summaries, collection completion, recent additions, and started-set progress.

## Dedicated card detail enhancements

Added per-card Master Set variant checklists, owned-copy details, direct edit/move/delete actions, and batched attack-cost loading.

## Collector dashboard expansion

Added aggregate Master Set, missing-card, recent-addition, duplicate-card, and top-set metrics to the collector dashboard.

## Advanced collection search and filtering

Added global catalog search, composable collection filters, URL-persisted state, sortable results, and collection-query indexes.

## Wishlist and trade list

Added card and variant wishlists, owned-copy trade flags, search filters, dashboard widgets, and safe schema migration support.

## Collection analytics

Added aggregate collection analytics, interactive linked charts, set completion lists, duplicate ranking, and monthly growth reporting.

## Collection valuation and purchase tracking

Added per-copy purchase, valuation, insurance, and provider metadata; value filters; dashboard totals; and value/ROI analytics.

## Backup, export and import system

Added a backup workspace with versioned JSON and CSV exports for collections, inventory, wishlists, trades, purchases, and values; import preview, merge/replace handling, transaction rollback, automatic SQLite snapshots, backup history, and restore controls.

## User settings and preferences

Added extensible per-user preferences, a settings workspace, theme and image-size controls, collection sort and filter defaults, currency and date formatting, and configurable dashboard widget visibility and order.

## Image viewer and variant comparison

Added a responsive full-screen card viewer with high-resolution scans, zoom and pan, available scan selection, previous/next viewer navigation, lazy-loaded images, and side-by-side Master Set variant ownership comparison.
