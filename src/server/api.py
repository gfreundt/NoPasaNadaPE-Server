from datetime import datetime as dt
from flask import request, jsonify
import time

from src.utils.constants import EXTERNAL_AUTH_TOKEN


def version_select(self, version, timer_start):

    if version == "v1":
        return run_v1(self, timer_start)

    else:
        return jsonify(f"Version API {version} no soportada."), 404


def run_v1(self, timer_start):

    # mas adelante asociar con usuario
    perfil = "MAQ-001"

    # informacion de la solicitud
    token = request.args.get("token")
    solicitud = request.args.get("solicitud").lower()
    correo = request.args.get("correo")
    usuario = request.args.get("usuario")

    # casuistica de solicitud api
    autenticado = 1
    if token != EXTERNAL_AUTH_TOKEN:
        respuesta_mensaje = "Error en Token de Autorizacion."
        respuesta_codigo = 401
        autenticado = 0
    elif not correo:
        respuesta_mensaje = "Lista de correos en blanco o formato equivocado."
        respuesta_codigo = 400
    elif not usuario:
        respuesta_mensaje = "Se debe especificar el nombre del usuario autorizando."
        respuesta_codigo = 400
    else:
        respuesta_mensaje = "Correo autorizado."
        respuesta_codigo = 200

    # informacion necesaria para registro de la solicitud api en base de datos
    data = {
        "TipoSolicitud": solicitud,
        "Endpoint": "/api/v1",
        "Autenticado": autenticado,
        "UsuarioSolicitando": usuario,
        "RespuestaStatus": respuesta_codigo,
        "RespuestaMensaje": respuesta_mensaje,
        "RespuestaTiempo": time.perf_counter() - timer_start,
        "RespuestaTamano": 0.01,
    }

    # actualizar tabla de registro de consultas api y recibir correlativo de solicitud
    id_solicitud = update_api_log(self, data)

    # si solicitud de registro ha sido crrecta, actualizar tabla de clientes autorizados a inscribirse
    if respuesta_codigo == 200:
        self.db.cursor.execute(
            "INSERT INTO InfoClientesAutorizados VALUES (?,?,?)",
            (id_solicitud, correo, perfil),
        )

    # cambios permanentes en base de datos
    self.db.conn.commit()

    return jsonify(respuesta_mensaje), respuesta_codigo


def update_api_log(self, data):

    # completar data para registrar solicitud
    data.update(
        {
            "Timestamp": str(dt.now()),
            "DireccionIP": request.headers.get("X-Forwarded-For")
            or request.remote_addr,
            "Metodo": request.method,
        }
    )

    # registrar solicitud en base de datos
    _cmd = f'INSERT INTO StatusApiLogs ({", ".join([i for i in data.keys()])}) VALUES ({"?, "*(len(data)-1)}?)'
    self.db.cursor.execute(_cmd, tuple(i for i in data.values()))

    # devolver el indice para relacionar solicitud con autorizaciones
    return self.db.cursor.lastrowid
