from datetime import datetime as dt
from flask import request, jsonify
import time

from src.utils.constants import EXTERNAL_AUTH_TOKEN


def version_select(self, version, timer_start):

    if version == "v1":
        return run_v1(self, timer_start)

    return jsonify(f"Version API {version} no soportada."), 404


def run_v1(self, timer_start):

    # extract request data safely
    token = request.args.get("token")
    solicitud = (request.args.get("solicitud") or "").lower()
    correo = request.args.get("correo")
    usuario = request.args.get("usuario")

    log_data = {
        "TipoSolicitud": solicitud,
        "Endpoint": "/api/v1",
        "UsuarioSolicitando": usuario or "",
    }

    autenticado = True
    id_solicitud = None  # Track if alta already wrote a log

    # ========== TOKEN ERROR ==========
    if token != EXTERNAL_AUTH_TOKEN:
        return finalize(
            self,
            timer_start,
            log_data,
            "Error en Token de Autorizacion.",
            401,
            autenticado=False,
        )

    # ========== MISSING USER ==========
    if not usuario:
        return finalize(
            self,
            timer_start,
            log_data,
            "Se debe especificar el nombre del usuario autorizando.",
            400,
        )

    # ========== TEST USER ==========
    if usuario == "TST-00":
        return finalize(self, timer_start, log_data, "Prueba exitosa.", 200)

    # ========== REQUEST: INFO ==========
    if solicitud == "info":
        self.db.cursor.execute("SELECT Correo FROM InfoClientesAutorizados")
        registros = [dict(i) for i in self.db.cursor.fetchall()]
        return finalize(self, timer_start, log_data, registros, 200)

    # ========== INVALID EMPTY EMAIL ==========
    if not correo:
        return finalize(
            self, timer_start, log_data, "Correo en blanco o formato equivocado.", 400
        )

    # ========== REQUEST: ALTA (CREATE CLIENT) ==========
    if solicitud == "alta":

        respuesta_mensaje = f"Correo: {correo} autorizado."
        respuesta_codigo = 200

        perfil = "MAQ-001"

        # Write log BEFORE inserting new authorized client
        id_solicitud = update_api_log(
            self,
            build_log_entry(
                log_data,
                respuesta_codigo,
                respuesta_mensaje,
                timer_start,
                autenticado=True,
            ),
        )

        # Now add authorized client
        self.db.cursor.execute(
            "INSERT INTO InfoClientesAutorizados VALUES (?,?,?)",
            (id_solicitud, correo, perfil),
        )
        self.db.conn.commit()

        return jsonify(respuesta_mensaje), respuesta_codigo

    # ========== REQUEST: BAJA (DELETE CLIENT) ==========
    if solicitud == "baja":

        self.db.cursor.execute(
            "DELETE FROM InfoClientesAutorizados WHERE Correo = ?",
            (correo,),
        )

        rows_deleted = self.db.cursor.rowcount

        if rows_deleted > 0:
            self.db.conn.commit()
            msg = f"Correo: {correo} eliminado correctamente."
            code = 200
        else:
            msg = f"Correo: {correo} no encontrado."
            code = 404

        return finalize(self, timer_start, log_data, msg, code)

    # ========== UNKNOWN REQUEST ==========
    return finalize(self, timer_start, log_data, "Error en solicitud.", 400)


# =============================================================
# HELPERS
# =============================================================


def finalize(self, timer_start, log_data, mensaje, codigo, autenticado=True):
    """
    Safely write the API log (unless alta already wrote it)
    and return the final API response.
    """

    entry = build_log_entry(log_data, codigo, mensaje, timer_start, autenticado)

    update_api_log(self, entry)

    return jsonify(mensaje), codigo


def build_log_entry(log_data, code, msg, timer_start, autenticado):
    """
    Prepares a complete log row with timing, IP, and response metadata.
    """
    entry = dict(log_data)  # copy

    entry.update(
        {
            "Autenticado": int(autenticado),
            "RespuestaStatus": code,
            "RespuestaMensaje": str(msg)[:30],
            "RespuestaTiempo": time.perf_counter() - timer_start,
            "RespuestaTamano": 0.01,
            "Timestamp": str(dt.now()),
            "DireccionIP": request.headers.get("X-Forwarded-For")
            or request.remote_addr,
            "Metodo": request.method,
        }
    )

    return entry


def update_api_log(self, log_data):
    """
    Inserts a row into StatusApiLogs and returns rowid.
    """

    columns = ", ".join(log_data.keys())
    placeholders = ", ".join("?" for _ in log_data)

    cmd = f"INSERT INTO StatusApiLogs ({columns}) VALUES ({placeholders})"
    self.db.cursor.execute(cmd, tuple(log_data.values()))
    return self.db.cursor.lastrowid
