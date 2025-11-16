from datetime import datetime as dt
from flask import request, jsonify
import time
import re
import json

from src.utils.constants import EXTERNAL_AUTH_TOKEN


def version_select(self, version, timer_start):

    if version == "v1":
        return run_v1(self, timer_start)

    return jsonify(f"Version API {version} no soportada."), 404


def run_v1(self, timer_inicio):

    try:

        cursor = self.db.cursor()

        _data = request.get_json()

        # extract request data safely
        token = _data.get("token")
        solicitud = (_data.get("solicitud") or "").lower()
        usuario = _data.get("usuario")
        clientes = _data.get("clientes")

        # calcular el secuencial para esta solicitud de api
        cursor.execute(
            "SELECT IdSolicitud FROM StatusApiLogs ORDER BY IdSolicitud DESC LIMIT 1"
        )
        _last = cursor.fetchone()

        data_log = {
            "IdSolicitud": _last[0] + 1 if _last else 0,
            "TipoSolicitud": solicitud,
            "Endpoint": "/api/v1",
            "UsuarioSolicitando": usuario or "",
        }

        # ========== ERROR: TOKEN NOT RECOGNIZED ==========
        if token != EXTERNAL_AUTH_TOKEN:
            return finalizar(
                self,
                timer_inicio,
                data_log,
                mensaje={"error": "Token de autorizacion incorrecto."},
                codigo=401,
                autenticado=False,
            )

        # ========== ERROR: INVALID REQUEST ==========
        if solicitud not in ("alta", "baja", "info"):
            return finalizar(
                self,
                timer_inicio,
                data_log,
                mensaje={"error": "Solicitud incorrecta (alta, baja, info)."},
                codigo=404,
                autenticado=True,
            )

        # ========== ERROR: MISSING USER ==========
        if not usuario:
            return finalizar(
                self,
                timer_inicio,
                data_log,
                mensaje={"error": "Usuario autorizando incorrecto."},
                codigo=400,
                autenticado=True,
            )

        # ========== CHECK: TEST USER ==========
        if usuario == "TST-000":
            return finalizar(
                self,
                timer_inicio,
                data_log,
                mensaje={"error": "Prueba exitosa."},
                codigo=200,
                autenticado=True,
            )

        # ========== REQUEST: INFO ==========
        if solicitud == "info":
            cursor.execute("SELECT * FROM InfoClientesAutorizados")
            rows = cursor.fetchall()
            column_names = [col[0] for col in cursor.description]
            registros = [dict(zip(column_names, row)) for row in rows]

            return finalizar(
                self,
                timer_inicio,
                data_log,
                mensaje={"data": registros},
                codigo=200,
                autenticado=True,
            )

        # ========== ERROR: INVALID EMPTY CLIENTES ==========
        if not isinstance(clientes, list) or len(clientes) == 0:
            return finalizar(
                self,
                timer_inicio,
                data_log,
                mensaje={"error": "Estructura de data de clientes equivocada."},
                codigo=400,
                autenticado=True,
            )

        # ========== REQUEST: ALTA / BAJA ==========
        respuesta_exitos = []
        respuesta_fallos = []
        perfil_interno = "MAQ-000"  # cambiar cuando hayan mas perfiles, asociados a usuario solicitando

        # cargar todos los correos activos en base de datos
        cursor.execute("SELECT Correo FROM InfoClientesAutorizados")
        correos_activos = set(i["Correo"] for i in cursor.fetchall())

        for indice, cliente in enumerate(clientes):

            # data no es un diccionario - saltar cliente
            if not isinstance(cliente, dict):
                respuesta_fallos.append(
                    {"indice": indice, "errores": ["Data mal estructurada"]}
                )
                continue

            # extraer data opcional (campos pueden estar vacios)
            nombre = cliente.get("nombre")
            tipo_doc = cliente.get("tipo_doc")
            numero_doc = cliente.get("numero_doc")
            celular = cliente.get("celular")
            codigo_externo = cliente.get("codigo_externo")

            # data es diccionario - extraer correo y hacer validaciones
            correo = cliente.get("correo")

            # campo de correo vacio
            if not correo:
                respuesta_fallos.append(
                    {
                        "indice": indice,
                        "errores": ["Campo de correo es obligatorio."],
                    }
                )

            # correo no cumple formato correcto
            elif not isinstance(correo, str) or not re.match(
                r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", correo
            ):
                respuesta_fallos.append(
                    {
                        "indice": indice,
                        "errores": ["Correo no cumple con formato."],
                    }
                )

            # correo ya esta en base de datos
            elif correo in correos_activos and solicitud == "alta":
                respuesta_fallos.append(
                    {
                        "indice": indice,
                        "errores": [
                            "Correo ya esta activo. Borrar antes de enviar nuevamente."
                        ],
                    }
                )

            # activar cliente (alta)
            elif solicitud == "alta":

                # agregar autorizacion a bd
                cmd = """   INSERT INTO InfoClientesAutorizados
                            (IdSolicitud, Correo, NombreCompleto, TipoDocumento, NumeroDocumento, Celular, CodigoClienteExterno, PerfilInterno)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                      """
                cursor.execute(
                    cmd,
                    (
                        data_log["IdSolicitud"],
                        correo,
                        nombre,
                        tipo_doc,
                        numero_doc,
                        celular,
                        codigo_externo,
                        perfil_interno,
                    ),
                )

                # activacion de este cliente exitoso
                respuesta_exitos.append({"indice": indice, "correo": correo})

            # desactivar cliente (baja)
            elif solicitud == "baja":

                # buscar correo en bd
                cursor.execute(
                    "DELETE FROM InfoClientesAutorizados WHERE Correo = ?",
                    (correo,),
                )
                rows_deleted = cursor.rowcount

                # si existe, eliminar y desactivacion exitosa
                if rows_deleted > 0:

                    respuesta_exitos.append({"indice": indice, "correo": correo})

                # no existe, desactivacion fallida
                else:
                    respuesta_fallos.append(
                        {
                            "indice": indice,
                            "errores": ["Correo no se encuentra."],
                        }
                    )

        self.db.conn.commit()

        # construir respuesta de la api, log en bd
        return finalizar(
            self,
            timer_inicio,
            data_log,
            autenticado=True,
            exitos=respuesta_exitos,
            fallos=respuesta_fallos,
        )

    except Exception as e:
        # ========== ERROR: NOT IDENTIFIED (CATCH EVERYTHING ELSE) ==========
        print(f"Api Error: {e}")
        return finalizar(
            self,
            timer_inicio,
            data_log,
            autenticado=True,
            mensaje={"error": "Error no especificado."},
            codigo=400,
        )


def finalizar(
    self,
    timer_inicio,
    data_log,
    autenticado,
    mensaje=None,
    codigo=None,
    exitos=None,
    fallos=None,
):

    #
    mensaje, codigo = construir_respuesta_api(data_log, exitos, fallos, codigo, mensaje)
    actualizar_log(
        self,
        data_log,
        autenticado,
        resultados=mensaje["resultados"],
        codigo=codigo,
        timer_inicio=timer_inicio,
    )

    return jsonify(mensaje), codigo


def construir_respuesta_api(data_log, exitos, fallos, codigo, mensaje):
    # error antes de empezar a procesar datos (codigo recibido)
    if codigo:
        _resultados = mensaje
        _codigo = codigo

    else:
        # error en todos los datos enviados
        if not exitos:
            _codigo = 400

        # sin errores en datos enviados
        elif not fallos:
            _codigo = 200

        # algunos con error, otros no
        else:
            _codigo = 207

        _resultados = {
            "cuenta_exitos": len(exitos),
            "cuenta_fallos": len(fallos),
            "exitos": exitos,
            "fallos": fallos,
        }

    return {
        "id_solicitud": data_log["IdSolicitud"],
        "tipo_solicitud": data_log["TipoSolicitud"],
        "endpoint": data_log["Endpoint"],
        "usuario_solicitando": data_log["UsuarioSolicitando"],
        "resultados": _resultados,
        "timestamp": str(dt.now()),
    }, _codigo


def actualizar_log(self, data_log, autenticado, resultados, codigo, timer_inicio):

    entry = dict(data_log)
    _ip = (
        request.headers.get("X-Forwarded-For")
        or request.headers.get("CF-Connecting-IP")
        or request.remote_addr
    )
    entry.update(
        {
            "Autenticado": int(autenticado),
            "RespuestaStatus": codigo,
            "RespuestaMensaje": json.dumps(resultados),
            "RespuestaTiempo": time.perf_counter() - timer_inicio,
            "RespuestaTamano": len(json.dumps(resultados)),
            "Timestamp": str(dt.now()),
            "DireccionIP": _ip,
            "Metodo": request.method,
        }
    )

    columns = ", ".join(entry.keys())
    placeholders = ", ".join("?" for _ in entry)

    cursor, conn = (self.db.cursor(), self.db.conn)
    cmd = f"INSERT INTO StatusApiLogs ({columns}) VALUES ({placeholders})"
    cursor.execute(cmd, tuple(entry.values()))
    conn.commit()
