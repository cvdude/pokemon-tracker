from flask import Flask

from routes.dashboard import dashboard
from routes.collection import collection
from routes.sets import sets
from routes.cards import cards
from routes.inventory import inventory

app = Flask(__name__)

app.register_blueprint(dashboard)
app.register_blueprint(collection)
app.register_blueprint(sets)
app.register_blueprint(cards)
app.register_blueprint(inventory)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)