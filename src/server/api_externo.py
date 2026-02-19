from flask import current_app, jsonify
from src.server import api_externo_v1


def version_select(version):
    """Enrutador de version de API que se usara"""

    db = current_app.db

    if version == "v1":
        return api_externo_v1.api(db)

    return jsonify(f"Version API {version} no soportada."), 404
