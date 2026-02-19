from datetime import datetime as dt
from flask import request, jsonify
import time
import re
import json
from security.keys import EXTERNAL_AUTH_TOKEN_API_V1
from src.comms import enviar_correo_inmediato

SQL_A_API = {
    "DireccionCorreo": "correo",
    "Correo": "correo",
    "FechaEnvio": "timestamp_envio",
    "RespuestaMensaje": "respuesta_mensaje",
    "Subject": "asunto",
    "TipoMensaje": "tipo_mensaje",
    "Celular": "celular",
    "CodigoClienteExterno": "codigo_cliente",
    "IdSolicitud": "id_solicitud",
    "NombreCompleto": "nombre",
    "NumeroDocumento": "numero_documento",
    "PerfilInterno": "perfil",
    "TimestampCreacion": "timestamp_creado",
    "TipoDocumento": "tipo_documento",
}


# --- FUNCION AUXILIAR PARA LIMPIAR DATOS ---
def clean_str(data, key, to_upper=False):
    """Extrae de forma segura una cadena de un dict, elimina espacios en blanco y maneja None."""
    val = data.get(key)
    if val is None:
        return ""
    val = str(val).strip()
    return val.upper() if to_upper else val


def api(db):

    timer_inicio = time.perf_counter()

    # Inicializar datos básicos de log en caso de fallo temprano
    data_log = {
        "IdSolicitud": 0,  # Marcador, se actualizará después de insertar en BD
        "TipoSolicitud": "",
        "Endpoint": "/api/v1",
        "UsuarioSolicitando": "",
    }

    try:
        # 1. Analizar Datos de la Solicitud
        _data = request.get_json() or {}

        # --- Obtener Token de la cabecera Authorization ---
        auth_header = request.headers.get("Authorization")
        token = None
        if auth_header and auth_header.startswith("Bearer "):
            # Extraer solo la parte del token (después de "Bearer ")
            token = auth_header.split(" ", 1)[1]

        # --- Obtener PArametros ---
        solicitud = clean_str(_data, "solicitud").lower()
        usuario = _data.get("usuario")
        clientes = _data.get("clientes")
        fecha_desde = _data.get("fecha_desde", dt(year=2000, month=1, day=1))
        fecha_hasta = _data.get("fecha_hasta", dt(year=2100, month=1, day=1))

        data_log["TipoSolicitud"] = solicitud
        data_log["UsuarioSolicitando"] = usuario or ""

        # 2. Conexión a Base de Datos
        cursor = db.cursor()
        conn = db.conn

        # --- CORRECCION: GENERACION DE ID SEGURA PARA HILOS ---
        # Insertar la entrada de log PRIMERO para generar un ID autoincremental único.
        # Esto previene condiciones de carrera donde dos solicitudes obtienen el mismo ID.
        cursor.execute(
            "INSERT INTO StatusApiLogs (Timestamp, Endpoint, UsuarioSolicitando) VALUES (?, ?, ?)",
            (str(dt.now()), "/api/v1", usuario or ""),
        )
        conn.commit()
        id_solicitud = cursor.lastrowid  # Obtener el ID generado por la BD
        data_log["IdSolicitud"] = id_solicitud

        # --- VALIDACIONES ---
        if token != EXTERNAL_AUTH_TOKEN_API_V1:
            return finalizar(
                db,
                timer_inicio,
                solicitud,
                data_log,
                codigo=401,
                autenticado=False,
                mensaje={"error": "Token incorrecto."},
            )

        if solicitud not in (
            "alta",
            "baja",
            "clientes_autorizados",
            "mensajes_enviados",
        ):
            return finalizar(
                db,
                timer_inicio,
                solicitud,
                data_log,
                codigo=404,
                autenticado=True,
                mensaje={"error": "Solicitud incorrecta."},
            )

        if not usuario:
            return finalizar(
                db,
                timer_inicio,
                solicitud,
                data_log,
                codigo=400,
                autenticado=True,
                mensaje={"error": "Usuario requerido."},
            )

        if usuario == "TST-000":
            return finalizar(
                db,
                timer_inicio,
                solicitud,
                data_log,
                codigo=200,
                autenticado=True,
                mensaje={"error": "Prueba exitosa."},
            )

        # --- SOLICITUD: BASE DE DATOS DE CLIENTES AUTORIZADOS ---
        if solicitud == "clientes_autorizados":
            cmd = """SELECT A.*, 
                        CASE WHEN B.Correo IS NOT NULL
                            THEN 1
                            ELSE 0
                        END AS inscrito
                        FROM InfoClientesAutorizados AS A
                        LEFT JOIN
                        InfoMiembros AS B
                        ON
                        A.Correo = B.Correo"""
            cursor.execute(cmd)
            rows = cursor.fetchall()
            column_names = [SQL_A_API.get(col[0], col[0]) for col in cursor.description]
            registros = [dict(zip(column_names, row)) for row in rows]
            return finalizar(
                db,
                timer_inicio,
                solicitud,
                data_log,
                codigo=200,
                autenticado=True,
                mensaje={"data": registros, "cuenta": len(registros)},
            )

        # --- SOLICITUD: BASE DE DATOS DE MENSAJES ENVIADOS ---
        if solicitud == "mensajes_enviados":
            cmd = """ SELECT TipoMensaje, DireccionCorreo, Subject, FechaEnvio, RespuestaMensaje FROM StatusMensajesEnviados
                        WHERE FechaEnvio BETWEEN ? AND ?
                    """
            cursor.execute(cmd, (fecha_desde, fecha_hasta))
            rows = cursor.fetchall()
            column_names = [SQL_A_API.get(col[0], col[0]) for col in cursor.description]
            registros = [dict(zip(column_names, row)) for row in rows]
            return finalizar(
                db,
                timer_inicio,
                solicitud,
                data_log,
                codigo=200,
                autenticado=True,
                mensaje={"data": registros, "cuenta": len(registros)},
            )

        # --- SOLICITUD: ALTA / BAJA ---
        if not isinstance(clientes, list) or len(clientes) == 0:
            return finalizar(
                db,
                timer_inicio,
                solicitud,
                data_log,
                codigo=400,
                autenticado=True,
                mensaje={"error": "Lista de clientes invalida."},
            )

        respuesta_exitos = []
        respuesta_fallos = []

        # --- OPTIMIZACION: PRE-CARGA MASIVA (Arreglo N+1) ---
        # En lugar de consultar dentro del bucle, consultamos UNA VEZ para todas las coincidencias.
        existing_emails = set()
        existing_docs = set()  # Almacena tupla: (TipoDoc, NumDoc)
        existing_codes = set()

        if solicitud == "alta" and len(clientes) > 0:
            # 1. Obtener todos los correos/docs entrantes para verificar
            incoming_emails = [
                clean_str(c, "correo").lower() for c in clientes if c.get("correo")
            ]
            incoming_codes = [
                clean_str(c, "codigo_externo", True)
                for c in clientes
                if c.get("codigo_externo")
            ]

            # 2. Consulta Masiva de Correos
            if incoming_emails:
                placeholders = ",".join(["?"] * len(incoming_emails))
                cursor.execute(
                    f"SELECT Correo FROM InfoClientesAutorizados WHERE Correo IN ({placeholders})",
                    tuple(incoming_emails),
                )
                existing_emails = {row[0] for row in cursor.fetchall()}

            # 3. Consulta Masiva de Códigos Externos
            if incoming_codes:
                placeholders = ",".join(["?"] * len(incoming_codes))
                cursor.execute(
                    f"SELECT CodigoClienteExterno FROM InfoClientesAutorizados WHERE CodigoClienteExterno IN ({placeholders})",
                    tuple(incoming_codes),
                )
                existing_codes = {row[0] for row in cursor.fetchall()}

            # 4. Nota: Los documentos son más difíciles de verificar masivamente si los tipos varían mezclados con números,
            # pero si es necesario podríamos hacer una verificación IN similar en los números.
            # Por ahora, almacenaremos los números en caché para minimizar el impacto.
            incoming_nums = [
                clean_str(c, "numero_documento")
                for c in clientes
                if c.get("numero_documento")
            ]
            if incoming_nums:
                placeholders = ",".join(["?"] * len(incoming_nums))
                cursor.execute(
                    f"SELECT TipoDocumento, NumeroDocumento, Correo FROM InfoClientesAutorizados WHERE NumeroDocumento IN ({placeholders})",
                    tuple(incoming_nums),
                )
                # Mapear (Tipo, Num) -> Correo (para mensaje de error)
                for row in cursor.fetchall():
                    existing_docs.add((str(row[0]), str(row[1]), row[2]))

        # --- BUCLE PRINCIPAL DE PROCESAMIENTO ---
        for index, cliente in enumerate(clientes):
            if not isinstance(cliente, dict):
                respuesta_fallos.append(
                    {"indice": index, "errores": ["Data mal estructurada"]}
                )
                continue

            # Limpiar entradas
            nombre = clean_str(cliente, "nombre")
            tipo_documento = clean_str(cliente, "tipo_documento")
            numero_documento = clean_str(cliente, "numero_documento")
            celular = clean_str(cliente, "celular")
            perfil_interno = clean_str(cliente, "perfil")
            codigo_externo = clean_str(cliente, "codigo_externo", to_upper=True)
            correo = clean_str(cliente, "correo").lower()

            errores_cliente = []

            # Validación Básica
            if not correo:
                errores_cliente.append("Campo de correo obligatorio.")
            elif not re.match(
                r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", correo
            ):
                errores_cliente.append("Correo invalido.")

            if nombre and (
                not (5 < len(nombre) < 50)
                or not re.match(r"^[a-zA-Z\u00C0-\u00FF\s\-\']+$", nombre)
            ):
                errores_cliente.append("Nombre invalido.")

            if tipo_documento and tipo_documento not in ("DNI", "CE", "PASAPORTE"):
                errores_cliente.append(
                    "Tipo de Documento Invalido (valido: 'DNI', 'CE', 'PASAPORTE')"
                )

            if (
                tipo_documento == "DNI" and not re.match(r"^\d{8}$", numero_documento)
            ) or (
                tipo_documento == "CE" and not re.match(r"^\d{12}$", numero_documento)
            ):
                errores_cliente.append("Numero de Documento Invalido.")

            if celular and not re.match(r"^\d{9}$", celular):
                errores_cliente.append("Celular Invalido.")

            # Si la validación falla, saltar verificaciones de BD
            if errores_cliente:
                respuesta_fallos.append({"indice": index, "errores": errores_cliente})
                continue

            # --- LOGICA PARA ALTA ---
            if solicitud == "alta":
                # Verificar Caché Local (Búsqueda Rápida O(1))
                if correo in existing_emails:
                    respuesta_fallos.append(
                        {"indice": index, "errores": ["Correo ya activo."]}
                    )
                    continue

                if codigo_externo in existing_codes:
                    respuesta_fallos.append(
                        {"indice": index, "errores": ["Codigo externo ya activo."]}
                    )
                    continue

                # Verificar coincidencia de tupla de Documento en nuestra caché
                doc_conflict = next(
                    (
                        x
                        for x in existing_docs
                        if x[0] == tipo_documento and x[1] == numero_documento
                    ),
                    None,
                )
                if doc_conflict:
                    respuesta_fallos.append(
                        {
                            "indice": index,
                            "errores": [
                                f"Documento ya activo (asociado a {doc_conflict[2]})."
                            ],
                        }
                    )
                    continue

                # Agregar al Lote (No hacer commit aún)
                cmd = """INSERT INTO InfoClientesAutorizados 
                         (IdSolicitud, Correo, NombreCompleto, TipoDocumento, NumeroDocumento, Celular, CodigoClienteExterno, PerfilInterno, TimestampCreacion) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"""
                cursor.execute(
                    cmd,
                    (
                        id_solicitud,
                        correo,
                        nombre,
                        tipo_documento,
                        numero_documento,
                        celular,
                        codigo_externo,
                        perfil_interno,
                        str(dt.now()),
                    ),
                )

                # Actualizar caché local en caso de duplicados dentro de la MISMA lista de solicitud
                existing_emails.add(correo)
                respuesta_exitos.append({"indice": index, "correo": correo})

            # --- LOGICA PARA BAJA ---
            elif solicitud == "baja":
                cursor.execute(
                    "DELETE FROM InfoClientesAutorizados WHERE Correo = ?", (correo,)
                )
                if cursor.rowcount > 0:
                    respuesta_exitos.append({"indice": index, "correo": correo})
                else:
                    respuesta_fallos.append(
                        {
                            "indice": index,
                            "errores": ["Correo no encontrado."],
                        }
                    )

        # --- COMMIT FINAL ---
        # Guardar todos los cambios a la vez. Rápido.
        conn.commit()

        return finalizar(
            db,
            timer_inicio,
            solicitud,
            data_log,
            autenticado=True,
            exitos=respuesta_exitos,
            fallos=respuesta_fallos,
        )

    except Exception as e:
        print(f"Error de API: {e}")

        return finalizar(
            db,
            timer_inicio,
            solicitud,
            data_log,
            autenticado=True,
            mensaje={"error": "Error interno."},
            codigo=500,
        )


def finalizar(
    db,
    timer_inicio,
    solicitud,
    data_log,
    autenticado,
    mensaje=None,
    codigo=None,
    exitos=None,
    fallos=None,
):
    # Determinar Código de Estado basado en resultados
    if codigo:
        _codigo = codigo
        resultados = mensaje
    else:
        if not exitos:
            _codigo = 400
        elif not fallos:
            _codigo = 200
        else:
            _codigo = 207  # Multi-Estado

        resultados = {
            "cuenta_exitos": len(exitos or []),
            "cuenta_fallos": len(fallos or []),
            "exitos": exitos or [],
            "fallos": fallos or [],
        }

    # Preparar Actualización Final de Log
    entry = dict(data_log)
    _ip = request.headers.get("X-Forwarded-For") or request.remote_addr

    # 1. Serializar a JSON
    respuesta_json = json.dumps(resultados)

    # 2. Calcular tamaño en KB reales (utf-8)
    tamano_kilobytes = round(len(respuesta_json.encode("utf-8")) / 1024, 4)

    entry.update(
        {
            "Autenticado": int(autenticado),
            "RespuestaStatus": _codigo,
            "RespuestaMensaje": respuesta_json,
            "RespuestaTamanoKb": tamano_kilobytes,
            "RespuestaTiempoSeg": time.perf_counter() - timer_inicio,
            "DireccionIP": _ip,
            "Metodo": request.method,
            "Timestamp": str(dt.now()),
        }
    )

    # Actualizar la entrada de log existente
    cursor = db.cursor()
    conn = db.conn

    cmd = """UPDATE StatusApiLogs SET TipoSolicitud=?, Timestamp=?, DireccionIP=?, Metodo=?, Endpoint=?, Autenticado=?, UsuarioSolicitando=?, RespuestaStatus=?, RespuestaTiempoSeg=?, RespuestaTamanoKb=?, RespuestaMensaje=?
             WHERE IdSolicitud=?"""

    cursor.execute(
        cmd,
        (
            entry["TipoSolicitud"],
            entry["Timestamp"],
            entry["DireccionIP"],
            entry["Metodo"],
            entry["Endpoint"],
            entry["Autenticado"],
            entry["UsuarioSolicitando"],
            entry["RespuestaStatus"],
            entry["RespuestaTiempoSeg"],
            entry["RespuestaTamanoKb"],
            entry["RespuestaMensaje"],
            entry["IdSolicitud"],
        ),
    )
    conn.commit()

    # enviar correos de activacion a usuario
    if exitos and solicitud == "alta":
        for item in exitos:
            enviar_correo_inmediato.activacion(db, item["correo"])

    elif exitos and solicitud == "baja":
        for item in exitos:
            enviar_correo_inmediato.desactivacion(db, item["correo"], nombre=None)

    return (
        jsonify(
            {
                "id_solicitud": entry["IdSolicitud"],
                "timestamp": entry["Timestamp"],
                "resultados": resultados,
            }
        ),
        _codigo,
    )
