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

    # informacion de la solicitud
    token = request.args.get("token")
    solicitud = request.args.get("solicitud").lower()
    correo = request.args.get("correo")
    usuario = request.args.get("usuario")

    data = {
        "TipoSolicitud": solicitud,
        "Endpoint": "/api/v1",
        "UsuarioSolicitando": usuario,
    }

    # casuistica de solicitud api
    autenticado = True

    if token != EXTERNAL_AUTH_TOKEN:
        respuesta_mensaje = "Error en Token de Autorizacion."
        respuesta_codigo = 401
        autenticado = False

    elif not usuario:
        respuesta_mensaje = "Se debe especificar el nombre del usuario autorizando."
        respuesta_codigo = 400

    elif solicitud == "info":
        self.db.cursor.execute("SELECT Correo FROM InfoClientesAutorizados")
        respuesta_mensaje = [dict(i) for i in self.db.cursor.fetchall()]
        respuesta_codigo = 200

    elif not correo:
        respuesta_mensaje = "Lista de correos en blanco o formato equivocado."
        respuesta_codigo = 400

    elif solicitud == "alta":

        respuesta_mensaje = f"Correo: {correo} autorizado."
        respuesta_codigo = 200

        # mas adelante asociar con usuario
        perfil = "MAQ-001"

        # informacion necesaria para registro de la solicitud api en base de datos
        data.update(
            {
                "Autenticado": int(autenticado),
                "RespuestaStatus": respuesta_codigo,
                "RespuestaMensaje": str(respuesta_mensaje)[:30],
                "RespuestaTiempo": time.perf_counter() - timer_start,
                "RespuestaTamano": 0.01,
            }
        )

        # actualizar tabla de registro de consultas api y recibir correlativo de solicitud
        id_solicitud = update_api_log(self, data)

        # si solicitud de registro ha sido correcta, actualizar tabla de clientes autorizados a inscribirse
        self.db.cursor.execute(
            "INSERT INTO InfoClientesAutorizados VALUES (?,?,?)",
            (id_solicitud, correo, perfil),
        )
        self.db.conn.commit()

    elif solicitud == "baja":

        # intentar borrar correo
        self.db.cursor.execute(
            "DELETE FROM InfoClientesAutorizados WHERE Correo = ?",
            (correo,),
        )

        # determinar filas afectadas
        rows_deleted = self.db.cursor.rowcount

        if rows_deleted > 0:
            # filas afectadas: grabar cambios
            respuesta_mensaje = f"Correo: {correo} eliminado correctamente."
            respuesta_codigo = 200
            self.db.conn.commit()
        else:
            # filas no afectadas: no hay cambios
            respuesta_mensaje = f"Correo: {correo} no encontrado."
            respuesta_codigo = 404

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
