import logging
from pprint import pformat, pprint
from src.updates import configuracion_plazos
from datetime import datetime as dt

logger = logging.getLogger(__name__)


def get_datos_alertas(self):
    cte1_estructura = [
        {
            "tabla": "DataApesegSoats",
            "placa_select": True,
            "dias": "-18, -9, -2, 0, 1, 2, 3",
            "last_update": "LastUpdateApesegSoats",
        },
        {
            "tabla": "DataMtcRevisionesTecnicas",
            "placa_select": True,
            "dias": "-21, -11, -2, 0, 1, 2, 3",
            "last_update": "LastUpdateMtcRevisionesTecnicas",
        },
        {
            "tabla": "DataMtcBrevetes",
            "placa_select": False,
            "dias": "-30, -15, -2, 0, 1, 2, 3",
            "last_update": "LastUpdateMtcBrevetes",
        },
        {
            "tabla": "DataSatImpuestosCodigos a JOIN DataSatImpuestosDeudas b ON a.Codigo = b.Codigo",
            "placa_select": False,
            "dias": "-18, -7, -2, 0, 1, 2, 3",
            "last_update": "LastUpdateSatImpuestosCodigos",
        },
    ]

    cte1 = []

    # crear sub-query para cada tabla
    for tabla in cte1_estructura:

        cmd = f"""  SELECT '{tabla['tabla']}' as Categoria, 
                    {"PlacaValidate" if tabla.get('placa_select') else "NULL"} as Placa,
                    {"(SELECT IdMember_FK FROM InfoPlacas WHERE PlacaValidate = Placa)" if tabla.get('placa_select') else "IdMember_FK"} as IdMember,
                    FechaHasta
                    FROM {tabla['tabla']} 
                    WHERE
                """

        cmd += (
            f"DATE ({'FechaHasta'}) IN ("
            + ",\n ".join(
                f"DATE('now','localtime', '{-int(n):+d} days')"
                for n in tabla["dias"].split(", ")
            )
            + ")"
        )

        cte1.append(cmd)

    # unir todos los sub-querys y crear select final que unifica todo y extrae datos de documentos
    cte1 = "\n\nUNION ALL\n\n".join(cte1)

    cte2_estructura = {
        "ventana_ultima_alerta_dias": 1,
    }

    cte2_estructura = f""" SELECT IdMember FROM StatusMensajesEnviados
                WHERE
                TipoMensaje = "ALERTA" AND
                DATE(FechaEnvio) > DATE('now','localtime','-{cte2_estructura["ventana_ultima_alerta_dias"]} days')
             """

    select = """
        SELECT 
        c.Categoria, 
        c.Placa, 
        c.IdMember,
        c.FechaHasta,
        m.DocNum, 
        m.DocTipo,
        m.Correo
    FROM TodasAlertas c
    JOIN infomiembros m ON c.IdMember = m.idmember; """

    # consolidar query final
    query = f"""WITH TodasAlertas AS ({cte1}), 
                    AlertasRecientes AS ({cte2_estructura})
                    {select}"""

    # extrae informacion de base de datos
    cursor = self.db.cursor()
    cursor.execute(query)
    # resultado = cursor.fetchall()

    return [{i: j for i, j in dict(k).items()} for k in cursor.fetchall()]


def get_boletines_para_actualizar(self):

    cte = """   SELECT IdMember FROM InfoMiembros
	            WHERE DATE(NextMessageSend) <= DATE('now','localtime')"""

    cmds = []

    select_estructura = [
        {
            "tabla": "DataApesegSoats",
            "placa_select": True,
            "fecha_hasta": True,
        },
        {
            "tabla": "DataMtcRevisionesTecnicas",
            "placa_select": True,
            "fecha_hasta": True,
        },
        {
            "tabla": "DataMtcBrevetes",
            "fecha_hasta": True,
            "placa_select": False,
        },
        {
            "tabla": "DataSatImpuestosCodigos a JOIN DataSatImpuestosDeudas b ON a.Codigo = b.Codigo",
            "fecha_hasta": False,
            "placa_select": False,
        },
        {
            "tabla": "DataSatMultas",
            "fecha_hasta": False,
            "placa_select": True,
        },
        {
            "tabla": "DataSutranMultas",
            "fecha_hasta": False,
            "placa_select": True,
        },
        {
            "tabla": "DataMtcRecordsConductores",
            "fecha_hasta": False,
            "placa_select": False,
        },
        {
            "tabla": "DataCallaoMultas",
            "fecha_hasta": False,
            "placa_select": True,
        },
    ]

    for tabla in select_estructura:

        cola = (
            f""" AND NOT EXISTS (
                    SELECT 1
                    FROM {tabla['tabla']} s
                    WHERE {'s.PlacaValidate = p.Placa' if tabla['placa_select'] else 's.IdMember_FK = m.IdMember'}
                    AND DATE(s.FechaHasta) > DATE('now','localtime', '+30 days')
                    )
                """
            if tabla["fecha_hasta"]
            else ""
        )

        cmd = f"""  SELECT DISTINCT
                    '{tabla['tabla']}' AS Categoria,
                    {"p.Placa" if tabla.get('placa_select') else "NULL"} as Placa,
                    m.IdMember
                    FROM InfoMiembros m
                    JOIN InfoPlacas p
                        ON p.IdMember_FK = m.IdMember
                    WHERE DATE(m.NextMessageSend) <= DATE('now','localtime')
                    {cola}
                """

        cmds.append(cmd)

    cmds = "\n\nUNION ALL\n\n".join(cmds)

    query = f"""SELECT 
                        c.Categoria, 
                        c.Placa, 
                        c.IdMember,
                        m.DocNum, 
                        m.DocTipo,
                        m.Correo
                        FROM (
                            (
                        {cmds}
                                ) c 
                            JOIN Infomiembros m 
                            ON c.IdMember = m.Idmember);"""

    # extrae informacion de base de datos
    cursor = self.db.cursor()
    cursor.execute(query)
    # resultado = cursor.fetchall()

    return [{i: j for i, j in dict(k).items()} for k in cursor.fetchall()]


def get_boletines_para_mensajes(self):

    cmd = """
            SELECT IdMember, DocTipo, DocNum, Correo
                FROM InfoMiembros 
                WHERE DATE(NextMessageSend) <= DATE('now','localtime')
            """
    cursor = self.db.cursor()
    cursor.execute(cmd)
    return [dict(i) for i in cursor.fetchall()]
