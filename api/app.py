from flask import Flask

from models.collection import ensure_collection_schema
from routes.dashboard import dashboard
from routes.collection import collection
from routes.sets import sets
from routes.cards import cards
from routes.inventory import inventory
from routes.analytics import analytics
from routes.backup import backup


app = Flask(__name__)

ensure_collection_schema()

app.register_blueprint(dashboard)
app.register_blueprint(collection)
app.register_blueprint(sets)
app.register_blueprint(cards)
app.register_blueprint(inventory)
app.register_blueprint(analytics)
app.register_blueprint(backup)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
