CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value TEXT
);
CREATE TABLE series (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    sort_order INTEGER
);
CREATE TABLE sqlite_sequence(name,seq);
CREATE TABLE sets (
    id TEXT PRIMARY KEY,
    series_id INTEGER,
    name TEXT NOT NULL,
    release_date TEXT,
    printed_total INTEGER,
    total INTEGER,
    logo TEXT,
    symbol TEXT, github_url TEXT, total_cards INTEGER, symbol_url TEXT, logo_url TEXT, tcgdex_id TEXT, api_id TEXT,
    FOREIGN KEY (series_id) REFERENCES series(id)
);
CREATE TABLE cards (
    id TEXT PRIMARY KEY,
    set_id TEXT NOT NULL,
    number TEXT,
    name TEXT NOT NULL,
    rarity TEXT,
    artist TEXT,
    hp TEXT,
    stage TEXT,
    evolves_from TEXT,
    regulation_mark TEXT,
    image_small TEXT,
    image_large TEXT, category TEXT, suffix TEXT, dex_id TEXT, illustrator TEXT, updated_at TEXT,
    FOREIGN KEY (set_id) REFERENCES sets(id)
);
CREATE TABLE collection (
    variant_id INTEGER PRIMARY KEY,
    owned INTEGER DEFAULT 0,
    binder_qty INTEGER DEFAULT 0,
    master_qty INTEGER DEFAULT 0,
    trade_qty INTEGER DEFAULT 0,
    condition TEXT,
    location TEXT,
    notes TEXT,
    FOREIGN KEY (variant_id) REFERENCES variants(id)
);
CREATE TABLE card_images
(
    card_id TEXT PRIMARY KEY,
    small TEXT,
    large TEXT,
    FOREIGN KEY(card_id) REFERENCES cards(id)
);
CREATE TABLE card_types
(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id TEXT,
    type TEXT,
    FOREIGN KEY(card_id) REFERENCES cards(id)
);
CREATE TABLE card_subtypes
(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id TEXT,
    subtype TEXT,
    FOREIGN KEY(card_id) REFERENCES cards(id)
);
CREATE TABLE abilities
(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id TEXT,
    ability_type TEXT,
    name TEXT,
    text TEXT,
    FOREIGN KEY(card_id) REFERENCES cards(id)
);
CREATE TABLE attacks
(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id TEXT,
    attack_order INTEGER,
    name TEXT,
    damage TEXT,
    text TEXT,
    FOREIGN KEY(card_id) REFERENCES cards(id)
);
CREATE TABLE attack_cost
(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attack_id INTEGER,
    energy TEXT,
    position INTEGER,
    FOREIGN KEY(attack_id) REFERENCES attacks(id)
);
CREATE TABLE weaknesses
(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id TEXT,
    type TEXT,
    value TEXT,
    FOREIGN KEY(card_id) REFERENCES cards(id)
);
CREATE TABLE resistances
(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id TEXT,
    type TEXT,
    value TEXT,
    FOREIGN KEY(card_id) REFERENCES cards(id)
);
CREATE TABLE retreat_cost
(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id TEXT,
    energy TEXT,
    position INTEGER,
    FOREIGN KEY(card_id) REFERENCES cards(id)
);
CREATE TABLE locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT
);
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    email TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    card_id TEXT NOT NULL,
    variant_id TEXT,
    location_id INTEGER NOT NULL,
    condition_id INTEGER,
    quantity INTEGER NOT NULL DEFAULT 1,
    is_graded INTEGER NOT NULL DEFAULT 0,
    favorite INTEGER NOT NULL DEFAULT 0,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(card_id) REFERENCES cards(id),
    FOREIGN KEY(location_id) REFERENCES locations(id)
);
CREATE TABLE variants (
    id TEXT PRIMARY KEY,
    card_id TEXT NOT NULL,
    variant_type TEXT,
    subtype TEXT,
    stamp TEXT,
    size TEXT,
    FOREIGN KEY(card_id) REFERENCES cards(id)
);

CREATE TABLE collection_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 1,
    card_id TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    condition TEXT NOT NULL DEFAULT 'Near Mint',
    variant TEXT NOT NULL DEFAULT 'Normal',
    custom_variant TEXT,
    language TEXT NOT NULL DEFAULT 'English',
    ownership_type TEXT NOT NULL DEFAULT 'Raw',
    grading_company TEXT,
    custom_grading_company TEXT,
    grade REAL,
    certification_number TEXT,
    is_trade INTEGER NOT NULL DEFAULT 0,
    storage_location TEXT NOT NULL DEFAULT 'Unassigned',
    acquisition_date TEXT,
    purchase_price REAL,
    purchase_date TEXT,
    purchase_source TEXT,
    estimated_value REAL,
    previous_estimated_value REAL,
    last_valuation_date TEXT,
    valuation_source TEXT,
    insurance_value REAL,
    currency TEXT NOT NULL DEFAULT 'USD',
    notes TEXT,
    is_favorite INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (card_id) REFERENCES cards(id)
);

CREATE INDEX idx_collection_items_card_user
ON collection_items (card_id, user_id);

CREATE TABLE wishlist_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 1,
    card_id TEXT NOT NULL,
    source_variant_id TEXT,
    priority TEXT NOT NULL DEFAULT 'Medium',
    desired_condition TEXT,
    target_price REAL,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (card_id) REFERENCES cards(id)
);

CREATE TABLE backup_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL UNIQUE,
    operation TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    file_size INTEGER NOT NULL DEFAULT 0,
    notes TEXT
);

CREATE INDEX idx_backup_history_created
ON backup_history (created_at DESC);
