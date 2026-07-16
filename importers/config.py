from pathlib import Path

BASE_DIR = Path("/volume1/web/pokemon-tracker")

DATABASE = BASE_DIR / "database" / "pokemon.db"

DATA = BASE_DIR / "cards-database" / "cards-database-master" / "data"

TCGDEX_API = "https://api.tcgdex.net/v2/en"

IMAGE_BASE = "https://assets.tcgdex.net/en"

HEADERS = {
    "User-Agent": "EvoDeck Importer"
}