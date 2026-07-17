from datetime import datetime

from flask import Flask, g

from models.collection import ensure_collection_schema
from models.settings import ensure_settings_schema, get_settings
from routes.dashboard import dashboard
from routes.collection import collection
from routes.sets import sets
from routes.cards import cards
from routes.inventory import inventory
from routes.analytics import analytics
from routes.backup import backup
from routes.settings import settings


app = Flask(__name__)

ensure_collection_schema()
ensure_settings_schema()


@app.before_request
def load_user_preferences():
    g.preferences = get_settings()


@app.context_processor
def inject_user_preferences():
    preferences = g.preferences
    view_routes = {"catalog": "/collection?ownership=all", "collection": "/collection", "dashboard": "/"}
    return {"preferences": preferences, "default_collection_url": view_routes[preferences["default_collection_view"]]}


@app.template_filter("money")
def money(value):
    value = float(value or 0)
    currency = g.preferences["currency"]
    symbols = {"USD": "$", "CAD": "CA$", "EUR": "€", "GBP": "£", "JPY": "¥", "AUD": "A$"}
    return f"{symbols[currency]}{value:,.0f}" if currency == "JPY" else f"{symbols[currency]}{value:,.2f}"


@app.template_filter("display_date")
def display_date(value):
    if not value:
        return "—"
    text = str(value)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text
    formats = {"YYYY-MM-DD": "%Y-%m-%d", "MM/DD/YYYY": "%m/%d/%Y", "DD/MM/YYYY": "%d/%m/%Y"}
    return parsed.strftime(formats[g.preferences["date_format"]])

app.register_blueprint(dashboard)
app.register_blueprint(collection)
app.register_blueprint(sets)
app.register_blueprint(cards)
app.register_blueprint(inventory)
app.register_blueprint(analytics)
app.register_blueprint(backup)
app.register_blueprint(settings)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
