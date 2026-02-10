import logging

logger = logging.getLogger(__name__)


def get_datos_alertas(self, premensaje):
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
            "tabla": "DataSatImpuestos",
            "placa_select": False,
            "dias": "-18, -7, -2, 0, 1, 2, 3",
            "last_update": "LastUpdateSatImpuestos",
        },
    ]

    cte1 = []

    # crear sub-query para cada tabla
    for tabla in cte1_estructura:
        last_update = tabla["tabla"].replace("Data", "LastUpdate")

        cmd = f"""  SELECT '{tabla["tabla"]}' as Categoria, 
                    {"PlacaValidate" if tabla.get("placa_select") else "NULL"} as Placa,
                    {"(SELECT IdMember_FK FROM InfoPlacas WHERE PlacaValidate = Placa)" if tabla.get("placa_select") else "IdMember_FK"} as IdMember,
                    FechaHasta,
                    {f"(SELECT {last_update} FROM InfoPlacas WHERE PlacaValidate = Placa)" if tabla.get("placa_select") else "IdMember_FK"} as LastUpdate
                    FROM {tabla["tabla"]} 
                    WHERE
                """

        cmd += (
            f" DATE ({'FechaHasta'}) IN ("
            + ",\n ".join(
                f"DATE('now','localtime', '{-int(n):+d} days')"
                for n in tabla["dias"].split(", ")
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
    {"AND DATE(c.LastUpdate) < DATE('now','localtime')" if premensaje else ""}; """

    # consolidar query final
    query = f"""WITH TodasAlertas AS ({cte1}), 
                    AlertasRecientes AS ({cte2})
                    {select}"""

    # extrae informacion de base de datos
    cursor = self.db.cursor()
    cursor.execute(query)
    # resultado = cursor.fetchall()

    return [{i: j for i, j in dict(k).items()} for k in cursor.fetchall()]


def get_datos_boletines(self, premensaje):

    if premensaje:
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
                "tabla": "DataSatImpuestos",
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
            last_update = tabla["tabla"].replace("Data", "LastUpdate")

            cola = (
                f""" AND NOT EXISTS (
                        SELECT 1
                        FROM {tabla["tabla"]} s
                        WHERE {"s.PlacaValidate = p.Placa" if tabla["placa_select"] else "s.IdMember_FK = m.IdMember"}
                        AND DATE(s.FechaHasta) >= DATE('now','localtime', '+30 days')
                        )
                    """
                if tabla["fecha_hasta"]
                else ""
            )

            cmd = f"""  SELECT DISTINCT
                        '{tabla["tabla"]}' AS Categoria,
                        {"p.Placa" if tabla.get("placa_select") else "NULL"} as Placa,
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
                                (
                            {cmds}
                                    ) c 
                                JOIN Infomiembros m 
                                ON c.IdMember = m.Idmember);"""

        # extrae informacion de base de datos

        cursor = self.db.cursor()
        cursor.execute(query)

        return [{i: j for i, j in dict(k).items()} for k in cursor.fetchall()]

    else:
        cmd = """
                SELECT IdMember, DocTipo, DocNum, Correo
                    FROM InfoMiembros 
                    WHERE DATE(NextMessageSend) <= DATE('now','localtime')
                """
        cursor = self.db.cursor()
        cursor.execute(cmd)
        return [dict(i) for i in cursor.fetchall()]
