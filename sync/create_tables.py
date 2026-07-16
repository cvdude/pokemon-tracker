from database import cursor

conn, cur = cursor()

# ----------------------------------------------------------
# Card Images
# ----------------------------------------------------------

cur.execute("""
CREATE TABLE IF NOT EXISTS card_images
(
    card_id TEXT PRIMARY KEY,
    small TEXT,
    large TEXT,
    FOREIGN KEY(card_id) REFERENCES cards(id)
)
""")

# ----------------------------------------------------------
# Card Types
# ----------------------------------------------------------

cur.execute("""
CREATE TABLE IF NOT EXISTS card_types
(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id TEXT,
    type TEXT,
    FOREIGN KEY(card_id) REFERENCES cards(id)
)
""")

# ----------------------------------------------------------
# Card Subtypes
# ----------------------------------------------------------

cur.execute("""
CREATE TABLE IF NOT EXISTS card_subtypes
(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id TEXT,
    subtype TEXT,
    FOREIGN KEY(card_id) REFERENCES cards(id)
)
""")

# ----------------------------------------------------------
# Abilities
# ----------------------------------------------------------

cur.execute("""
CREATE TABLE IF NOT EXISTS abilities
(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id TEXT,
    ability_type TEXT,
    name TEXT,
    text TEXT,
    FOREIGN KEY(card_id) REFERENCES cards(id)
)
""")

# ----------------------------------------------------------
# Attacks
# ----------------------------------------------------------

cur.execute("""
CREATE TABLE IF NOT EXISTS attacks
(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id TEXT,
    attack_order INTEGER,
    name TEXT,
    damage TEXT,
    text TEXT,
    FOREIGN KEY(card_id) REFERENCES cards(id)
)
""")

# ----------------------------------------------------------
# Attack Cost
# ----------------------------------------------------------

cur.execute("""
CREATE TABLE IF NOT EXISTS attack_cost
(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attack_id INTEGER,
    energy TEXT,
    position INTEGER,
    FOREIGN KEY(attack_id) REFERENCES attacks(id)
)
""")

# ----------------------------------------------------------
# Weaknesses
# ----------------------------------------------------------

cur.execute("""
CREATE TABLE IF NOT EXISTS weaknesses
(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id TEXT,
    type TEXT,
    value TEXT,
    FOREIGN KEY(card_id) REFERENCES cards(id)
)
""")

# ----------------------------------------------------------
# Resistances
# ----------------------------------------------------------

cur.execute("""
CREATE TABLE IF NOT EXISTS resistances
(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id TEXT,
    type TEXT,
    value TEXT,
    FOREIGN KEY(card_id) REFERENCES cards(id)
)
""")

# ----------------------------------------------------------
# Retreat Cost
# ----------------------------------------------------------

cur.execute("""
CREATE TABLE IF NOT EXISTS retreat_cost
(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id TEXT,
    energy TEXT,
    position INTEGER,
    FOREIGN KEY(card_id) REFERENCES cards(id)
)
""")

# ----------------------------------------------------------
# Variants
# ----------------------------------------------------------

cur.execute("""
CREATE TABLE IF NOT EXISTS variants
(
    card_id TEXT PRIMARY KEY,
    normal INTEGER,
    reverse INTEGER,
    holo INTEGER,
    first_edition INTEGER,
    unlimited INTEGER,
    FOREIGN KEY(card_id) REFERENCES cards(id)
)
""")

conn.commit()
conn.close()

print("Database updated successfully.")