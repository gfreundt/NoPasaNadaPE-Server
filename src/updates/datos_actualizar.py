from src.scrapers import configuracion_scrapers
import logging

logger = logging.getLogger(__name__)


def get_datos_alertas(db, premensaje):
    tablas = [
        "DataApesegSoats",
        "DataMtcRevisionesTecnicas",
        "DataMtcBrevetes",
        "DataSatImpuestos",
        "DataMaquinariasMantenimiento",
    ]

    # crear sub-query para cada tabla
    cte1 = []
    for tabla in tablas:
        config = configuracion_scrapers.config(tabla)
        last_update = tabla.replace("Data", "LastUpdate")

        cmd = f"""  SELECT '{tabla}' as Categoria, 
                    {"PlacaValidate" if config.get("indice_placa") else "NULL"} as Placa,
                    {"(SELECT IdMember_FK FROM InfoPlacas WHERE PlacaValidate = Placa)" if config.get("indice_placa") else "IdMember_FK"} as IdMember,
                    {config["campo_fecha_hasta"]},
                    {f"(SELECT {last_update} FROM InfoPlacas WHERE PlacaValidate = Placa)" if config.get("indice_placa") else "LastUpdate"} as LastUpdate
                    FROM {tabla} 
                    WHERE
                """

        cmd += (
            f" DATE ({config['campo_fecha_hasta']}) IN ("
            + ",\n ".join(
                f"DATE('now','localtime', '{-int(n):+d} days')"
                for n in config["alerta_dias"].split(", ")
            )
            + ")"
        )

        cte1.append(cmd)

    # unir todos los sub-querys y crear select final que unifica todo y extrae datos de documentos
    cte1 = "\n\nUNION ALL\n\n".join(cte1)

    cte2 = """ SELECT IdMember FROM StatusMensajesEnviados
                WHERE
                TipoMensaje = "ALERTA" AND
                DATE(FechaEnvio) = DATE('now','localtime')
            """

    select = f"""
                SELECT 
                c.Categoria, 
                c.Placa, 
                c.IdMember,
                c.FechaHasta,
                c.LastUpdate,
                m.DocNum, 
                m.DocTipo,
                m.Correo
                FROM TodasAlertas c
                JOIN Infomiembros m ON c.IdMember = m.Idmember
                WHERE c.IdMember NOT IN AlertasRecientes
                {"AND DATE(c.LastUpdate) < DATE('now','localtime')" if premensaje else ""};
            """

    # consolidar query final
    query = f"""
                    WITH TodasAlertas AS ({cte1}), 
                    AlertasRecientes AS ({cte2})
                    {select}
                 """

    # extrae informacion de base de datos
    cursor = db.cursor()
    cursor.execute(query)
    return [{i: j for i, j in dict(k).items()} for k in cursor.fetchall()]


def get_datos_boletines(db, premensaje):

    if premensaje:
        cmds = []

        tablas = [
            "DataApesegSoats",
            "DataMtcRevisionesTecnicas",
            "DataMtcBrevetes",
            "DataSatImpuestos",
            "DataMaquinariasMantenimiento",
            "DataSatMultas",
            "DataSutranMultas",
            "DataMtcRecordsConductores",
            "DataCallaoMultas",
        ]

        for tabla in tablas:
            config = configuracion_scrapers.config(tabla)
            last_update = tabla.replace("Data", "LastUpdate")

            cola = (
                f""" AND NOT EXISTS (
                        SELECT 1
                        FROM {tabla} s
                        WHERE {"s.PlacaValidate = p.Placa" if config["indice_placa"] else "s.IdMember_FK = m.IdMember"}
                        AND DATE(s.{config["campo_fecha_hasta"]}) >= DATE('now','localtime', '+30 days')
                        )
                    """
                if config["campo_fecha_hasta"]
                else ""
            )

            cmd = f"""  SELECT DISTINCT
                        '{tabla}' AS Categoria,
                        {"p.Placa" if config["indice_placa"] else "NULL"} as Placa,
                        m.IdMember
                        FROM InfoMiembros m
                        JOIN InfoPlacas p
                            ON p.IdMember_FK = m.IdMember
                        WHERE DATE(m.NextMessageSend) <= DATE('now','localtime')
                        AND {last_update} < DATE('now','localtime')
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
                           ({cmds}) c 
                            JOIN Infomiembros m 
                            ON c.IdMember = m.Idmember);"""

        cursor = db.cursor()
        cursor.execute(query)

        return [{i: j for i, j in dict(k).items()} for k in cursor.fetchall()]

    else:
        cmd = """
                SELECT IdMember, DocTipo, DocNum, Correo
                    FROM InfoMiembros 
                    WHERE DATE(NextMessageSend) <= DATE('now','localtime')
                """
        cursor = db.cursor()
        cursor.execute(cmd)
        return [dict(i) for i in cursor.fetchall()]
