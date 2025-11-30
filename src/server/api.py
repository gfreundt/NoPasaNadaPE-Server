from flask import jsonify
from src.server import api_v1


def version_select(self, version, timer_start):

    if version == "v1":
        return api_v1.api(self, timer_start)

    return jsonify(f"Version API {version} no soportada."), 404
