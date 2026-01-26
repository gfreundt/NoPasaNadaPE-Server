from pprint import pprint

sql = [
    {
        "select": "'soat' as Categoria, PlacaValidate as Placa, NULL as IdMember FROM DataApesegSoats",
        "dias": "-18, -9, -2, 0, 1, 2, 3",
        "indice": "Placa",
        "last_update": "LastUpdateApesegSoats",
    },
    {
        "select": "'revtec' as Categoria, PlacaValidate as Placa, NULL as IdMember FROM DataMtcRevisionesTecnicas",
        "dias": "-21, -11, -2, 0, 1, 2, 3",
        "indice": "Placa",
        "last_update": "LastUpdateMtcRevisionesTecnicas",
    },
    {
        "select": "'brevete' as Categoria, IdMember_FK as IdMember, NULL as Placa FROM DataMtcBrevetes",
        "dias": "-30, -15, -2, 0, 1, 2, 3",
        "indice": "IdMember",
        "last_update": "LastUpdateMtcBrevetes",
    },
    {
        "select": "'satimp' as Categoria, NULL as PlacaValidate, IdMember_FK as IdMember FROM DataSatImpuestosCodigos a JOIN DataSatImpuestosDeudas b ON a.Codigo = b.Codigo",
        "dias": "-18, -7, -2, 0, 1, 2, 3",
        "indice": "IdMember",
        "last_update": "LastUpdateSatImpuestosCodigos",
    },
]
cmds = []
for tabla in sql:

    cmd = f"SELECT {tabla['select']} WHERE "

    cmd += " OR ".join(
        f"DATE({'FechaHasta'}) = DATE('now','localtime', '{-int(n):+d} days')"
        for n in tabla["dias"].split(", ")
    )

    cmds.append(cmd)

cmds = "\nUNION ALL\n".join(cmds)

cmds = f"WITH unificada as ({cmds}) SELECT b.Categoria, b.Placa, a.IdMember, a.DocNum, a.DocTipo FROM unificada b LEFT JOIN InfoMiembros a ON a.IdMember = b.IdMember"


print(cmds)
