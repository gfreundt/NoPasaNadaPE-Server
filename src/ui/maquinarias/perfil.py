import re
from flask import redirect, request, render_template, url_for, session

from src.utils.utils import compare_text_to_hash, hash_text
from src.ui.maquinarias import servicios


# login endpoint
def main(self):

    # respuesta a pings para medir uptime
    if request.method == "HEAD":
        return ("", 200)

    # seguridad: evitar navegacion directa a url
    if session.get("etapa") != "validado":
        return redirect(url_for("maquinarias"))

    session["perfil_muestra_password"] = False

    self.session.permanent = True
    cursor = self.db.cursor()
    conn = self.db.conn

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

        errores = validaciones(self.db, forma)

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
        return servicios.main(self)


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
    for placa in forma.get("placas").split(", "):
        cursor.execute(
            """
            INSERT INTO InfoPlacas
            (IdMember_FK, Placa, LastUpdateApesegSoats, LastUpdateMtcRevisionesTecnicas, LastUpdateSunarpFichas, LastUpdateSutranMultas, LastUpdateSatMultas)
            VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(Placa) DO
                UPDATE SET IdMember_FK = excluded.IdMember_FK
            """,
            (
                id_member,
                placa,
                fecha_base,
                fecha_base,
                fecha_base,
                fecha_base,
                fecha_base,
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
            password_regex = r"^(?=.*[A-Z])(?=.*[\W_])(?=.{8,}).*$"

            if not re.match(password_regex, forma.get("password1", "")):
                errors["password1"] = (
                    "Contraseña debe tener mínimo 8 caracteres, "
                    "incluir una mayúscula y un carácter especial."
                )

            elif forma.get("password1") != forma.get("password2"):
                errors["password2"] = "Las contraseñas no coinciden."

    # --------------------------------------------------------------
    # limpieza final
    # --------------------------------------------------------------
    return {k: v for k, v in errors.items() if v}
