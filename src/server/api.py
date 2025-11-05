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
    id_solicitud = False
    token = request.args.get("token")
    solicitud = request.args.get("solicitud").lower()
    correo = request.args.get("correo")
    usuario = request.args.get("usuario")

    print(token, solicitud, correo, usuario)

    log_data = {
        "TipoSolicitud": solicitud,
        "Endpoint": "/api/v1",
        "UsuarioSolicitando": usuario,
    }

    # casuistica de solicitud api
    autenticado = True

    # error en token de seguridad
    if token != EXTERNAL_AUTH_TOKEN:
        respuesta_mensaje = "Error en Token de Autorizacion."
        respuesta_codigo = 401
        autenticado = False

    # error en usuario (en blanco)
    elif not usuario:
        respuesta_mensaje = "Se debe especificar el nombre del usuario autorizando."
        respuesta_codigo = 400

    # usuario de prueba TST-00
    elif log_data.get("UsuarioSolicitando") == "TST-00":
        respuesta_mensaje = "Prueba exitosa."
        respuesta_codigo = 200

    # solicitud de informacion de base de datos
    elif solicitud == "info":
        self.db.cursor.execute("SELECT Correo FROM InfoClientesAutorizados")
        respuesta_mensaje = [dict(i) for i in self.db.cursor.fetchall()]
        respuesta_codigo = 200

    # error en correo enviado (en blanco o no cumple con formato)
    elif not correo:
        respuesta_mensaje = "Correo en blanco o formato equivocado."
        respuesta_codigo = 400

    # solicitud de alta de cliente
    elif solicitud == "alta":
        respuesta_mensaje = f"Correo: {correo} autorizado."
        respuesta_codigo = 200

        # mas adelante asociar con usuario
        perfil = "MAQ-001"

        # informacion necesaria para registro de la solicitud api en base de datos
        log_data.update(
            {
                "Autenticado": int(autenticado),
                "RespuestaStatus": respuesta_codigo,
                "RespuestaMensaje": str(respuesta_mensaje)[:30],
                "RespuestaTiempo": time.perf_counter() - timer_start,
                "RespuestaTamano": 0.01,
            }
        )

        # actualizar tabla de registro de consultas api y recibir correlativo de solicitud
        id_solicitud = update_api_log(self, log_data)

        # si solicitud de registro ha sido correcta, actualizar tabla de clientes autorizados a inscribirse
        self.db.cursor.execute(
            "INSERT INTO InfoClientesAutorizados VALUES (?,?,?)",
            (id_solicitud, correo, perfil),
        )
        self.db.conn.commit()

    # solicitd de baja de cliente
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

    # error generico para casuisticas no especificas
    else:
        respuesta_mensaje = "Error en solicitud."
        respuesta_codigo = 400

    # registro de la solicitud api en base de datos (evitar en caso de alta porque ya se hizo)
    if not id_solicitud:
        log_data.update(
            {
                "Autenticado": int(autenticado),
                "RespuestaStatus": respuesta_codigo,
                "RespuestaMensaje": str(respuesta_mensaje)[:30],
                "RespuestaTiempo": time.perf_counter() - timer_start,
                "RespuestaTamano": 0.01,
            }
        )

    # actualizar tabla de registro de consultas api
    update_api_log(self, log_data)

    return jsonify(respuesta_mensaje), respuesta_codigo


def update_api_log(self, log_data):

    # completar data para registrar solicitud
    log_data.update(
        {
            "Timestamp": str(dt.now()),
            "DireccionIP": request.headers.get("X-Forwarded-For")
            or request.remote_addr,
            "Metodo": request.method,
        }
    )

    # registrar solicitud en base de datos
    _cmd = f'INSERT INTO StatusApiLogs ({", ".join([i for i in log_data.keys()])}) VALUES ({"?, "*(len(log_data)-1)}?)'
    self.db.cursor.execute(_cmd, tuple(i for i in log_data.values()))

    # devolver el indice para relacionar solicitud con autorizaciones
    return self.db.cursor.lastrowid
