import os
from datetime import datetime as dt
from flask import request, jsonify

from src.updates import get_records_to_update, get_recipients
from src.utils.constants import SQL_TABLES, NETWORK_PATH, UPDATER_TOKEN
from src.comms import craft_messages, send_messages_and_alerts, craft_alerts
from src.maintenance import maintenance


def update(self):

    post = request.json

    if post["token"] != UPDATER_TOKEN:
        print("Authentication Error")
        return "Auth Error!"

    if post["instruction"] == "get_records_to_update":
        return jsonify(get_records_to_update.get_records(self.db.cursor))

    if post["instruction"] == "do_updates":
        do_update(post["data"], self.db.cursor, self.db.conn)
        return "Update OK"

    if post["instruction"] == "create_messages":
        do_create_messages(self.db.cursor)
        _json = {}
        for msg in os.listdir(os.path.join(NETWORK_PATH, "outbound")):
            with open(os.path.join(NETWORK_PATH, "outbound", msg), mode="r") as file:
                _json.update({msg: file.read()})
        return jsonify(_json)

    if post["instruction"] == "send_messages":
        print("Client Request --> SEND MESSAGES")
        _json = send_messages_and_alerts.send(self.db.cursor, self.db.conn)
        return jsonify(_json)

    if post["instruction"] == "get_kpis":
        _json = do_get_kpis(self.db.cursor)
        return jsonify(_json)

    if post["instruction"] == "get_logs":
        _json = do_get_logs(self.db.cursor, max=post["max"])
        return jsonify(_json)

    if post["instruction"] == "get_info_data":
        _json = do_get_info_data(self.db.cursor)
        return jsonify(_json)


def do_update(data, db_cursor, db_conn):

    print("Client Request --> DO UPDATE")

    _now = dt.now().strftime("%Y-%m-%d")

    for table in data:

        # select table, key and foreign key for SQL commands
        if SQL_TABLES[table] == "DOC":
            info_table = "InfoMiembros"
            info_id = "IdMember"
            info_fk = "IdMember_FK"

        elif SQL_TABLES[table] == "PLACA":
            info_table = "InfoPlacas"
            info_id = "Placa"
            info_fk = "PlacaValidate"

        elif SQL_TABLES[table] == "COD":
            info_table = "InfoMiembros"
            info_id = "IdMember"
            info_fk = "Codigo"

        # get all unique foreign keys
        all_member_ids = tuple({f"{i[info_fk]}" for i in data[table]})

        # delete all previous records with same foreign key and update info table with latest update timestamp
        for id in all_member_ids:
            cmd1 = f"DELETE FROM {table} WHERE {info_fk} = '{id}'"
            cmd2 = ""
            if SQL_TABLES[table] in ("DOC", "PLACA"):
                cmd2 = f"UPDATE {info_table} SET LastUpdate{table[4:]} = '{_now}' WHERE {info_id} = '{id}';"
            db_cursor.executescript(f"{cmd1};{cmd2}")

        # loop an all records that need updating and insert them one by one unless it is empty
        for record in data[table]:
            if "Empty" not in record.keys():
                cmd = f"INSERT INTO {table} {tuple(record.keys())} VALUES {tuple(record.values())}"
                db_cursor.execute(cmd)

    db_conn.commit()


def do_create_messages(db_cursor):

    print("Client Request --> CREATE MESSAGES")

    get_recipients.need_alert(db_cursor)
    maintenance.clear_outbound_folder()
    craft_messages.craft(db_cursor)
    craft_alerts.craft(db_cursor)


def do_get_kpis(db_cursor):

    db_cursor.execute("SELECT COUNT(*) FROM InfoMiembros")
    total_miembros = db_cursor.fetchone()[0]

    db_cursor.execute("SELECT COUNT(*) FROM InfoPlacas")
    total_placas = db_cursor.fetchone()[0]

    # TODO: kpi truecaptcha

    return [{"total_miembros": total_miembros}, {"total_placas": total_placas}]


def do_get_logs(db_cursor, max):
    db_cursor.execute(f"SELECT * FROM StatusLogs ORDER BY Fecha DESC LIMIT {max}")
    latest_logs = db_cursor.fetchall()

    return {
        "latest_logs": [
            f"[{i['Fecha']}] {i['Tipo']}-{i['Ocurrencia']}" for i in latest_logs
        ]
    }


def do_get_info_data(db_cursor):
    # Get members
    db_cursor.execute("SELECT * FROM InfoMiembros")
    _miembros = [dict(row) for row in db_cursor.fetchall()]

    # Get plates
    db_cursor.execute("SELECT * FROM InfoPlacas")
    _placas = [dict(row) for row in db_cursor.fetchall()]

    return {"InfoMiembros": _miembros, "InfoPlacas": _placas}
