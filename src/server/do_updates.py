from datetime import datetime as dt
from src.utils.constants import SQL_TABLES


def main(db, data):

    cursor = db.cursor()
    conn = db.conn

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
            cursor.execute(f"DELETE FROM {table} WHERE {info_fk} = ?", (key,))
            if table_type in ("DOC", "PLACA"):

                field = f"LastUpdate{table[4:]}"
                cursor.execute(
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
            cursor.execute(sql, vals)

    conn.commit()
