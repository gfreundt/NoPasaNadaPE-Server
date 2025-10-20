from flask import redirect, request, render_template


def main(self):

    # cargando la data de la pagina
    if request.method == "GET":

        # in case no user data loaded
        if not self.session["loaded_user"]:
            self.load_user_data_into_session(self.session["login_correo"])

        # get member id for all the database searches
        member_id = self.session["loaded_user"]["IdMember"]
        data = {
            "auto": get_auto_data(self.db, member_id),
            "dni": get_dni_data(self.db, member_id),
            "pasaportes_visas": get_pasaportes_visas(self.db, member_id),
        }
        return render_template("cuenta-mis-vencimientos.html", data=data)

    # recibir cambios a informacion y guardar/no guardar
    elif request.method == "POST":
        process_form_response(
            db=self.db, member_id=self.session["loaded_user"]["IdMember"]
        )
        return redirect("mis-datos")


def process_form_response(db, member_id):

    # no graba en base de datos
    if request.form["accion"] == "cancelar":
        return

    # actualiza la informacion de DNI
    cmd = "UPDATE InfoMiembros SET FechaHastaDni = ? WHERE IdMember = ?"
    db.cursor.execute(cmd, (request.form["dni_fecha"], member_id))

    # actualiza la informacion de Pasaportes/Visas
    cmd = "DELETE FROM InfoPasaportesVisas WHERE IdMember_FK = ?"
    db.cursor.execute(cmd, (member_id,))
    for i in range(1, 4):
        if f"passportCountry{i}" in dict(request.form):
            db.cursor.execute(
                "INSERT INTO InfoPasaportesVisas VALUES (?,?,?)",
                (
                    member_id,
                    request.form[f"passportCountry{i}"],
                    request.form[f"passportDate{i}"],
                ),
            )

    db.conn.commit()


def get_auto_data(db, member_id):

    cmd = """
        SELECT 'Licencia de Conducir' AS titulo, Numero AS valor, FechaHasta
        FROM DataMtcBrevetes WHERE IdMember_FK = ?
        UNION
        SELECT 'Revision Tecnica', PlacaValidate, FechaHasta
        FROM DataMtcRevisionesTecnicas
        WHERE PlacaValidate IN (SELECT Placa FROM InfoPlacas WHERE IdMember_FK = ?)
        UNION
        SELECT 'SOAT', PlacaValidate, FechaHasta
        FROM DataApesegSoats
        WHERE PlacaValidate IN (SELECT Placa FROM InfoPlacas WHERE IdMember_FK = ?)
    """
    db.cursor.execute(cmd, (member_id, member_id, member_id))
    return [
        {
            "titulo": f"{row['titulo']} - {row['valor']}",
            "fecha": row["FechaHasta"],
        }
        for row in db.cursor.fetchall()
    ]


def get_dni_data(db, member_id):

    db.cursor.execute(
        "SELECT FechaHastaDni FROM InfoMiembros WHERE IdMember = ?", (member_id,)
    )
    row = db.cursor.fetchone()
    return (
        {"fecha": row["FechaHastaDni"]}
        if row and row["FechaHastaDni"]
        else {"fecha": None}
    )


def get_pasaportes_visas(db, member_id):

    db.cursor.execute(
        "SELECT Pais, FechaHasta FROM InfoPasaportesVisas WHERE IdMember_FK = ?",
        (member_id,),
    )
    rows = db.cursor.fetchall()
    return [{"pais": r["Pais"], "fecha": r["FechaHasta"]} for r in rows] if rows else []
