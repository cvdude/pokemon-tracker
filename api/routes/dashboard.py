from flask import Blueprint, render_template
import sqlite3

dashboard = Blueprint("dashboard", __name__)

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATABASE = BASE_DIR / "database" / "pokemon.db"

print("BASE_DIR =", BASE_DIR)
print("DATABASE =", DATABASE)
print("Exists =", DATABASE.exists())


@dashboard.route("/")
def home():

    conn = sqlite3.connect(str(DATABASE))
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM series")
    series = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM sets")
    sets = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM cards")
    cards = cur.fetchone()[0]

    conn.close()

    return render_template(
        "home.html",
        title="Dashboard",
        series=series,
        sets=sets,
        cards=cards,
    )