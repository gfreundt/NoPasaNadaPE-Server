# necesitan_mensajes.py
from src.updates.datos_actualizar import get_alertas_para_mensajes
from datetime import datetime as dt


def alertas(self):
    """
    Recupera una lista de miembros/placas que requieren una alerta.

    """
    return [
        {
            "IdMember": row["IdMember"],
            "TipoAlerta": ["TipoAlerta"],
            "Vencido": True if row["FechaHasta"] < dt.now() else False,
            "Placa": row["Placa"],
            "DocTipo": row["DocTipo"],
            "DocNum": row["DocNum"],
        }
        for row in get_alertas_para_mensajes(self)
    ]


def boletines(db_cursor):
    """
    Recupera una lista de diccionarios con los usuarios que requieren el boletín mensual.
    """

    cmd = """
    SELECT IdMember, DocTipo, DocNum, Correo
        FROM InfoMiembros 
        WHERE NextMessageSend <= datetime('now','localtime')
    """

    db_cursor.execute(cmd)
    rows = db_cursor.fetchall()

    if db_cursor.description:
        columns = [col[0] for col in db_cursor.description]
        results = [dict(zip(columns, row)) for row in rows]
    else:
        results = []

    return results
