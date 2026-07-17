"""Collection backup, export, import, and restore routes."""

import csv
import io
import json
from datetime import datetime
from pathlib import Path

from flask import Blueprint, Response, jsonify, render_template, request

from services.backup_service import (
    backup_history,
    csv_rows,
    export_payload,
    parse_import,
    preview_import,
    apply_import,
    restore_backup,
)


backup = Blueprint("backup", __name__)


@backup.route("/backup")
def backup_page():
    return render_template("backup.html", title="Backup, Export & Import", history=backup_history())


@backup.route("/backup/export/<export_type>/<export_format>")
def export_collection(export_type, export_format):
    try:
        payload = export_payload(export_type)
    except ValueError as error:
        return jsonify({"error": str(error)}), 404
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if export_format == "json":
        return Response(
            json.dumps(payload, indent=2),
            mimetype="application/json",
            headers={"Content-Disposition": f'attachment; filename="evodeck_{export_type}_{timestamp}.json"'},
        )
    if export_format == "csv":
        rows = csv_rows(payload)
        fields = sorted({field for row in rows for field in row} | {"record_type"})
        stream = io.StringIO()
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        return Response(
            stream.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f'attachment; filename="evodeck_{export_type}_{timestamp}.csv"'},
        )
    return jsonify({"error": "Unsupported export format."}), 404


def _uploaded_payload():
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        raise ValueError("Choose a JSON or CSV export file first.")
    return parse_import(uploaded.read(), Path(uploaded.filename).name)


@backup.route("/backup/import/preview", methods=["POST"])
def import_preview():
    try:
        payload = _uploaded_payload()
        return jsonify({"success": True, "format_version": payload["format_version"], "preview": preview_import(payload)})
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        return jsonify({"success": False, "error": str(error)}), 400


@backup.route("/backup/import", methods=["POST"])
def import_collection():
    try:
        payload = _uploaded_payload()
        result = apply_import(payload, request.form.get("mode", "merge"))
        return jsonify({"success": True, **result})
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        return jsonify({"success": False, "error": str(error)}), 400


@backup.route("/backup/restore/<int:backup_id>", methods=["POST"])
def restore_collection(backup_id):
    try:
        return jsonify({"success": True, **restore_backup(backup_id)})
    except ValueError as error:
        return jsonify({"success": False, "error": str(error)}), 404
