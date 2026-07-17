"""User preference page and JSON API."""

from flask import Blueprint, jsonify, redirect, render_template, request, url_for

from models.collection import DEFAULT_USER_ID
from models.settings import DEFAULT_SETTINGS, get_settings, save_settings


settings = Blueprint("settings", __name__)


def _form_values():
    filters = {"ownership": request.form.get("default_ownership", "owned")}
    for key in ("duplicates", "wishlist", "trade", "has_notes"):
        if request.form.get(f"filter_{key}"):
            filters[key] = True
    return {
        "default_collection_view": request.form.get("default_collection_view"),
        "theme": request.form.get("theme"),
        "card_image_size": request.form.get("card_image_size"),
        "default_sort": request.form.get("default_sort"),
        "default_order": request.form.get("default_order"),
        "default_filters": filters,
        "currency": request.form.get("currency"),
        "date_format": request.form.get("date_format"),
        "dashboard_widgets": request.form.getlist("dashboard_widgets"),
        "hidden_dashboard_widgets": request.form.getlist("hidden_dashboard_widgets"),
    }


@settings.route("/settings", methods=["GET", "POST"])
def settings_page():
    error = None
    preferences = get_settings(DEFAULT_USER_ID)
    if request.method == "POST":
        try:
            preferences = save_settings(_form_values(), DEFAULT_USER_ID)
            return redirect(url_for("settings.settings_page", saved="1"))
        except ValueError as exc:
            error = str(exc)
    return render_template("settings.html", title="Settings", preferences=preferences, defaults=DEFAULT_SETTINGS, error=error)


@settings.route("/api/settings", methods=["GET", "PATCH"])
def settings_api():
    if request.method == "GET":
        return jsonify({"settings": get_settings(DEFAULT_USER_ID)})
    try:
        return jsonify({"success": True, "settings": save_settings(request.get_json(silent=True) or {}, DEFAULT_USER_ID)})
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
