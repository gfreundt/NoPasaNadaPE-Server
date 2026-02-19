from datetime import datetime as dt
import os
import json
from src.scrapers import configuracion_scrapers
from src.utils.constants import NETWORK_PATH
import logging

logger = logging.getLogger(__name__)


def main(db, data):

    cursor = db.cursor()
    conn = db.conn

    HOY = dt.now().strftime("%Y-%m-%d")

    try:
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

            cursor.execute(cmd, val)

            # borrar registros de IdMember / PlacaValidate previos de tabla correspondiente
            cmd = f"DELETE FROM {tabla} WHERE {info_fk} = ?"
            val = (value_id,)
            cursor.execute(cmd, val)

            # si hay informacion de scraper, actualizar tabla - agregar primary key y LastUpdate
            for p in dato.get("Payload", []):
                cols = list(p.keys()) + [info_fk, "LastUpdate"]
                cmd = f"INSERT INTO {tabla} ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)})"
                val = tuple(p.values()) + (value_id, HOY)
                cursor.execute(cmd, val)

        conn.commit()
        logger.info(
            f"Base de datos correctamente actualizada con data de scrapers. Total registros = {len(data)}"
        )

    except Exception as e:
        logger.warning(f"No se pudo actualizar base de datos con data de scraper: {e}")

        # intentar grabar en archivo local
        update_files = [
            int(i[-10:-5])
            for i in os.listdir(os.path.join(NETWORK_PATH, "security"))
            if "update_" in i
        ]
        next_secuential = max(update_files) + 1 if update_files else 0
        path = os.path.join(
            NETWORK_PATH, "security", f"update_{next_secuential:05d}.json"
        )

        with open(path, mode="w") as outfile:
            outfile.write(json.dumps(data))
        logger.warning(f"Grabado localmente a {path}. Total registros = {len(data)}")
