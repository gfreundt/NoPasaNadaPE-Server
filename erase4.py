from pprint import pprint


def main():
    cte1_estructura = [
        {
            "categoria": "soat",
            "tabla": "DataApesegSoats",
            "placa_select": True,
            "dias": "-18, -9, -2, 0, 1, 2, 3",
            "indice": "Placa",
            "last_update": "LastUpdateApesegSoats",
        },
        {
            "categoria": "revtec",
            "tabla": "DataMtcRevisionesTecnicas",
            "placa_select": True,
            "dias": "-21, -11, -2, 0, 1, 2, 3",
            "indice": "Placa",
            "last_update": "LastUpdateMtcRevisionesTecnicas",
        },
        {
            "categoria": "brevete",
            "tabla": "DataMtcBrevetes",
            "placa_select": False,
            "dias": "-30, -15, -2, 0, 1, 2, 3",
            "indice": "IdMember",
            "last_update": "LastUpdateMtcBrevetes",
        },
        {
            "categoria": "satimp",
            "tabla": "DataSatImpuestosCodigos a JOIN DataSatImpuestosDeudas b ON a.Codigo = b.Codigo",
            "placa_select": False,
            "dias": "-18, -7, -2, 0, 1, 2, 3",
            "indice": "IdMember",
            "last_update": "LastUpdateSatImpuestosCodigos",
        },
    ]

    cte1 = []

    # crear sub-query para cada tabla
    for tabla in cte1_estructura:

        cmd = f"""  SELECT '{tabla['categoria']}' as Categoria, 
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
    return f"""WITH TodasAlertas AS ({cte1}), 
                    AlertasRecientes AS ({cte2_estructura})
                    {select}"""


print(main())
