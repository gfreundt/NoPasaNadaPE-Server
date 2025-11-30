import os
from datetime import datetime as dt
from flask import request, jsonify

from src.utils.constants import SQL_TABLES, NETWORK_PATH, UPDATER_TOKEN
from src.comms import send_messages_and_alerts, generar_mensajes
from src.maintenance import maintenance
from src.updates import datos_actualizar, necesitan_mensajes


def update(self):

    post = request.json or {}

    # ----- Auth Check -----
    if post.get("token") != UPDATER_TOKEN:
        print("Authentication Error")
        return jsonify({"error": "Auth Error"}), 401

    db_cursor, db_conn = self.db.cursor(), self.db.conn
    instruction = post.get("instruction")

    if instruction == "datos_alerta":
        return jsonify(datos_actualizar.alertas(db_cursor))

    if instruction == "datos_boletin":
        return jsonify(datos_actualizar.boletines(db_cursor))

    if instruction == "do_updates":
        do_update(post.get("data", {}), db_cursor, db_conn)
        return jsonify({"status": "Update OK"})

    if "generar" in instruction:

        # borrar /outbound
        maintenance.clear_outbound_folder()

        if instruction == "generar_alertas":
            print("Client Request --> GENERAR ALERTAS")
            maintenance.clear_outbound_folder("alertas")
            x = necesitan_mensajes.alertas(db_cursor)
            payload = generar_mensajes.alertas(db_cursor, x)

        elif instruction == "generar_boletines":
            print("Client Request --> GENERAR BOLETINES")
            maintenance.clear_outbound_folder("boletines")
            y = necesitan_mensajes.boletines(db_cursor)
            payload = generar_mensajes.boletines(db_cursor, y)

        # extraer copia de los mensajes generados para devolver a cliente
        # payload = {}
        # out_dir = os.path.join(NETWORK_PATH, "outbound")
        # for msg in os.listdir(out_dir):
        #     with open(os.path.join(out_dir, msg), "r") as f:
        #         payload[msg] = f.read()

        return jsonify(payload)

    if instruction == "send_messages":
        print("Client Request --> SEND MESSAGES")
        result = send_messages_and_alerts.send(db_cursor, db_conn)
        return jsonify(result)

    if instruction == "get_kpis":
        return jsonify(do_get_kpis(db_cursor))

    if instruction == "get_logs":
        return jsonify(do_get_logs(self.db.cursor, max=post.get("max", 50)))

    if instruction == "get_info_data":
        return jsonify(do_get_info_data(db_cursor))

    return jsonify({"error": "Unknown instruction"}), 400


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
