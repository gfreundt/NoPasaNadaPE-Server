from datetime import datetime as dt
import logging

from src.scrapers import configuracion_scrapers

logger = logging.getLogger(__name__)


def main(self, data):

    cursor = self.db.cursor()
    conn = self.db.conn

    HOY = dt.now().strftime("%Y-%m-%d")

    for dato in data:
        tabla = dato.get("Categoria")

        if configuracion_scrapers.config(tabla)["indice_placa"]:
            info_table = "InfoPlacas"
            info_id = "Placa"
            info_fk = "PlacaValidate"
            value_id = dato["Placa"]
        else:
            info_table = "InfoMiembros"
            info_id = "IdMember"
            info_fk = "IdMember_FK"
            value_id = dato["IdMember"]

        # actualizar fecha de LastUpdate de InfoMiembros o InfoPlacas para el dato correspondiente
        last_update_field = tabla.replace("Data", "LastUpdate")
        cmd = f"UPDATE {info_table} SET {last_update_field} = ? WHERE {info_id} = ?"
        val = (HOY, value_id)
        print(cmd, val)
        cursor.execute(cmd, val)

        # borrar registros de IdMember / PlacaValidate previos de tabla correspondiente
        cmd = f"DELETE FROM {tabla} WHERE {info_fk} = ?"
        val = (value_id,)
        print(cmd, val)
        cursor.execute(cmd, val)

        # si hay informacion de scraper, actualizar tabla - agregar LastUpdate
        for p in dato.get("Payload", []):
            cols = list(p.keys()) + ["LastUpdate"]
            cmd = f"INSERT INTO {tabla} ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)})"
            val = tuple(p.values()) + (HOY,)
            print(cmd, val)
            cursor.execute(cmd, val)

        conn.commit()
        print("---------------")
