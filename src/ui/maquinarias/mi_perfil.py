import re
from flask import current_app, redirect, request, render_template, url_for, session

from src.utils.constants import FORMATO_PASSWORD
from src.utils.utils import compare_text_to_hash, hash_text
from src.ui.maquinarias import mis_servicios


# login endpoint
def main():

    db = current_app.db

    # respuesta a pings para medir uptime
    if request.method == "HEAD":
        return ("", 200)

    # seguridad: evitar navegacion directa a url
    if session.get("etapa") != "validado":
        return redirect(url_for("maquinarias"))

    session["perfil_muestra_password"] = False
    session.permanent = True

    cursor = db.cursor()
    conn = db.conn

    if request.method == "GET":
        return render_template(
            "ui-maquinarias-mi-perfil.html",
            usuario=session["usuario"],
            show_password_field=session["perfil_muestra_password"],
            errors={},
            user_data={},
        )

    # POST — form submitted
    elif request.method == "POST":
        forma = dict(request.form)

        # procesar texto ingresados de placas lo mejor que se pueda
        if forma.get("placas"):
            x = re.sub(r"\s{1,}", ",", forma.get("placas")).replace(";", ",")
            forma["placas"] = ", ".join(
                [i.strip().upper() for i in x.split(",") if i.strip()]
            )

        usuario = {
            "correo": forma.get("correo"),
            "nombre": forma.get("nombre"),
            "tipo_documento": forma.get("tipo_documento"),
            "numero_documento": forma.get("numero_documento"),
            "celular": forma.get("celular"),
            "placas": forma.get("placas"),
        }

        errores = validaciones(db, forma)

        if errores:
            return render_template(
                "ui-maquinarias-mi-perfil.html",
                errors=errores,
                usuario=usuario,
                show_password_field=session["perfil_muestra_password"],
            )

        # No errors → proceed
        actualizar(cursor=cursor, conn=conn, forma=forma)
        session["usuario"].update(usuario)
        return mis_servicios.main()


def actualizar(cursor, conn, forma):

    id_member = session["usuario"]["id_member"]

    # grabar datos de miembro
    cmd = "UPDATE InfoMiembros SET NombreCompleto = ?, Celular = ? WHERE IdMember = ?"
    cursor.execute(cmd, (forma.get("nombre"), forma.get("celular"), id_member))

    # grabar nuevo password si hubo cambio
    if forma.get("password1"):
        cmd = "UPDATE InfoMiembros SET Password = ? WHERE IdMember = ?"
        cursor.execute(cmd, (hash_text(forma.get("password1")), id_member))

    # eliminar asociacion de miembro son todas las placas
    cmd = "UPDATE InfoPlacas SET IdMember_FK = 0 WHERE IdMember_FK = ?"
    cursor.execute(cmd, (id_member,))

    # volver a asociar miembro con las placas ingresadas
    # crear placas para nuevo miembro si no existe, si placa ya existe, asignar a este usuario
    fecha_base = "2020-01-01"
    placas = [
        i for i in (forma.get("placa1"), forma.get("placa2"), forma.get("placa3")) if i
    ]
    for k, placa in enumerate(placas, start=1):
        cursor.execute(
            """
            INSERT INTO InfoPlacas
            (IdMember_FK, Placa, LastUpdateApesegSoats, LastUpdateMtcRevisionesTecnicas, LastUpdateSunarpFichas, LastUpdateSutranMultas, LastUpdateSatMultas, AnoFabricacion)
            VALUES (?,?,?,?,?,?,?,?)
            ON CONFLICT(Placa) DO
                UPDATE SET IdMember_FK = excluded.IdMember_FK
            """,
            (
                id_member,
                placa.upper(),
                fecha_base,
                fecha_base,
                fecha_base,
                fecha_base,
                fecha_base,
                forma.get(f"ano_fabricacion{k}"),
            ),
        )

    conn.commit()


# ==================================================================
# VALIDATION
# ==================================================================
def validaciones(db, forma):

    cur = db.cursor()

    errors = {
        "nombre": "",
        "documento": "",
        "celular": "",
        "placas": "",
        "acepta_legales": "",
        "password1": "",
        "password2": "",
    }

    # --------------------------------------------------------------
    # nombre
    # --------------------------------------------------------------
    if len(forma["nombre"]) < 4:
        errors["nombre"] = "Nombre debe tener un mínimo de 4 caracteres."
    elif len(forma["nombre"]) > 50:
        errors["nombre"] = "Nombre debe tener un máximo de 50 caracteres."

    # --------------------------------------------------------------
    # celular
    # --------------------------------------------------------------
    if not re.match(r"^[0-9]{9}$", forma.get("celular", "")):
        errors["celular"] = "Celular debe tener 9 dígitos."
    else:
        cur.execute(
            "SELECT 1 FROM InfoMiembros WHERE Celular = ? AND Correo != ? LIMIT 1",
            (forma["celular"], forma["correo"]),
        )
        if cur.fetchone():
            errors["celular"] = "Celular ya está registrado"

    # --------------------------------------------------------------
    # placas
    # --------------------------------------------------------------
    if forma.get("placas"):
        _placas = forma["placas"].split(", ")

        if any(len(i) != 6 for i in _placas):
            errors["placas"] = "Todas las placas deben tener 6 caracteres."

        elif len(_placas) > 3:
            errors["placas"] = "Se pueden inscribir un máximo de 3 placas."

        # placa inscrita por otro usuario
        cur.execute(
            f"""
                SELECT 1 
                FROM InfoPlacas 
                WHERE 
                    Placa IN ({", ".join(["?"] * len(_placas))}) 
                    AND IdMember_FK != 0 
                    AND IdMember_FK != ? 
                LIMIT 1
             """,
            tuple(_placas) + (session["usuario"]["id_member"],),
        )

        if cur.fetchone():
            errors["placas"] = "Al menos una placa ya está inscrita por otro usuario."

    # --------------------------------------------------------------
    # password
    # --------------------------------------------------------------

    if forma.get("current_password"):
        session["perfil_muestra_password"] = True

        # revisar si usuario ingreso password vigente correctamente
        if not compare_text_to_hash(
            text_string=forma.get("current_password"),
            hash_string=session["usuario"]["password"],
        ):
            errors["current_password"] = "Contraseña equivocada"

        else:
            # revisar si nuevo password cumple con requisitos
            if not re.match(FORMATO_PASSWORD["regex"], forma.get("password1", "")):
                errors["password1"] = FORMATO_PASSWORD["mensaje"]

            elif forma.get("password1") != forma.get("password2"):
                errors["password2"] = "Las contraseñas no coinciden."

    # --------------------------------------------------------------
    # limpieza final
    # --------------------------------------------------------------
    return {k: v for k, v in errors.items() if v}
