from datetime import datetime as dt
from flask import request, jsonify

from src.utils.constants import SQL_TABLES
from security.keys import UPDATER_TOKEN
from src.comms import send_messages_and_alerts, generar_mensajes, enviar_correo_diferido
from src.maintenance import maintenance
from src.updates import datos_actualizar, necesitan_mensajes


def update(self):

    post = request.json or {}

    # ----- Auth Check -----
    if post.get("token") != UPDATER_TOKEN:
        print("Authentication Error")
        return jsonify({"error": "Auth Error"}), 401

    cursor, conn = self.db.cursor(), self.db.conn
    instruction = post.get("instruction")

    if instruction == "datos_alerta":
        return jsonify(datos_actualizar.alertas(cursor))

    if instruction == "datos_boletin":
        return jsonify(datos_actualizar.boletines(cursor))

    if instruction == "do_updates":
        do_update(post.get("data", {}), cursor, conn)
        return jsonify({"status": "Update OK"})

    if instruction == "generar_alertas":
        print("Client Request --> GENERAR ALERTAS")
        payload = generar_mensajes.alertas(cursor)
        return jsonify(payload)

    if instruction == "generar_boletines":
        print("Client Request --> GENERAR BOLETINES")
        payload = generar_mensajes.boletines(cursor)
        return jsonify(payload)

    if instruction == "send_messages":
        print("Client Request --> SEND MESSAGES")
        result = enviar_correo_diferido.send(cursor, conn)
        return jsonify(result)

    if instruction == "get_kpis":
        return jsonify(do_get_kpis(cursor))

    if instruction == "get_logs":
        return jsonify(do_get_logs(self.db.cursor, max=post.get("max", 50)))

    if instruction == "get_info_data":
        return jsonify(do_get_info_data(cursor))

    if instruction == "get_entire_db":
        return jsonify(do_get_entire_db(cursor))

    return jsonify({"error": "Instruccion desconocida"}), 400


# -------------------------------------------------------------------------
# ---------------------------  DO UPDATE  ---------------------------------
# -------------------------------------------------------------------------
def do_update(data, db_cursor, db_conn):

    today = dt.now().strftime("%Y-%m-%d")

    for table, rows in data.items():

        if table not in SQL_TABLES:
            continue

        table_type = SQL_TABLES[table]

        # Identify corresponding Info-table + keys
        if table_type == "DOC":
            info_table = "InfoMiembros"
            info_id = "IdMember"
            info_fk = "IdMember_FK"

        elif table_type == "PLACA":
            info_table = "InfoPlacas"
            info_id = "Placa"
            info_fk = "PlacaValidate"

        elif table_type == "COD":
            info_table = "InfoMiembros"
            info_id = "IdMember"
            info_fk = "Codigo"

        else:
            continue

        # Extract unique foreign keys from payload
        keys = {str(row.get(info_fk)) for row in rows if info_fk in row}
        keys = tuple(keys)

        # Delete old records + update timestamp
        for key in keys:
            db_cursor.execute(f"DELETE FROM {table} WHERE {info_fk} = ?", (key,))
            if table_type in ("DOC", "PLACA"):

                field = f"LastUpdate{table[4:]}"
                db_cursor.execute(
                    f"UPDATE {info_table} SET {field} = ? WHERE {info_id} = ?",
                    (today, key),
                )

        # Insert new rows
        for record in rows:
            if "Empty" in record:
                continue

            cols = list(record.keys())
            vals = list(record.values())
            placeholders = ", ".join("?" for _ in vals)

            sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})"
            db_cursor.execute(sql, vals)

    db_conn.commit()


# -------------------------------------------------------------------------
# ------------------------------ KPIS -------------------------------------
# -------------------------------------------------------------------------
def do_get_kpis(db_cursor):

    db_cursor.execute("SELECT COUNT(*) FROM InfoMiembros")
    total_miembros = db_cursor.fetchone()[0]

    db_cursor.execute("SELECT COUNT(*) FROM InfoPlacas")
    total_placas = db_cursor.fetchone()[0]

    return [{"total_miembros": total_miembros}, {"total_placas": total_placas}]


# -------------------------------------------------------------------------
# ------------------------------ LOGS -------------------------------------
# -------------------------------------------------------------------------
def do_get_logs(db_cursor, max):

    db_cursor.execute("SELECT * FROM StatusLogs ORDER BY Fecha DESC LIMIT ?", (max,))
    latest = db_cursor.fetchall()

    return {
        "latest_logs": [
            f"[{row['Fecha']}] {row['Tipo']}-{row['Ocurrencia']}" for row in latest
        ]
    }


# -------------------------------------------------------------------------
# ---------------------------- RAW DATA -----------------------------------
# -------------------------------------------------------------------------
def do_get_info_data(db_cursor):

    db_cursor.execute("SELECT * FROM InfoMiembros")
    members = [dict(r) for r in db_cursor.fetchall()]

    db_cursor.execute("SELECT * FROM InfoPlacas")
    plates = [dict(r) for r in db_cursor.fetchall()]

    return {"InfoMiembros": members, "InfoPlacas": plates}


def do_get_entire_db(cursor):
    """
    Retrieves all data from all non-system tables in an SQLite database
    and returns it as a single JSON string.
    """

    data_completa = {}

    # obtener el nombre de todas las tablas excepto las internas de SQLITE
    cmd = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
    cursor.execute(cmd)
    nombre_tablas = [row[0] for row in cursor.fetchall()]

    # iterar en cada tabla y extraer todos los datos
    for tabla in nombre_tablas:

        cmd = f"SELECT * FROM {tabla}"
        cursor.execute(cmd)
        rows = cursor.fetchall()

        # agregar resultado a variable recolectora
        data_completa.update({tabla: [dict(row) for row in rows]})

    return data_completa
