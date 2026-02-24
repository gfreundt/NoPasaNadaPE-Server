import re
from datetime import datetime as dt
from flask import current_app, redirect, request, render_template, url_for, session

from src.ui.maquinarias import login
from src.utils.constants import FORMATO_PASSWORD
from src.utils.utils import compare_text_to_hash, hash_text
from src.ui.maquinarias import mis_servicios, registro


# login endpoint
def main():

    # respuesta a pings para medir uptime
    if request.method == "HEAD":
        return ("", 200)

    # seguridad: evitar navegacion directa a url
    if session.get("etapa") != "validado":
        return redirect(url_for("maquinarias"))

    session["perfil_muestra_password"] = False
    session.permanent = True

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
        # define punteros de base de datos
        db = current_app.db
        cursor = db.cursor()
        conn = db.conn

        # extraer data de formulario
        forma = dict(request.form)
        print(forma)

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
            "placa1": forma.get("placa1"),
            "placa2": forma.get("placa2"),
            "placa3": forma.get("placa3"),
            "ano_fabricacion1": forma.get("ano_fabricacion1"),
            "ano_fabricacion2": forma.get("ano_fabricacion2"),
            "ano_fabricacion3": forma.get("ano_fabricacion3"),
            "password1": "",
            "password2": "",
        }

        errores = registro.validaciones(db, forma, mi_perfil=True)

        if errores:
            return render_template(
                "ui-maquinarias-mi-perfil.html",
                errors=errores,
                usuario=usuario,
                show_password_field=session["perfil_muestra_password"],
            )

        # sin errores --> proceder a actualizar datos de usuario
        actualizar(cursor=cursor, conn=conn, forma=forma)
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
            (   IdMember_FK,
                Placa,
                LastUpdateApesegSoats,
                LastUpdateMtcRevisionesTecnicas,
                LastUpdateSunarpFichas,
                LastUpdateSutranMultas,
                LastUpdateSatMultas,
                LastUpdateCallaoMultas,
                LastUpdateMaquinariasMantenimiento,
                AnoFabricacion)
            VALUES (?,?,?,?,?,?,?,?,?,?)
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
                fecha_base,
                fecha_base,
                forma.get(f"ano_fabricacion{k}"),
            ),
        )

    conn.commit()

    # volver a extraer data de usuario para actualizar session con nuevos datos
    login.extraer_data_usuario(cursor, correo=forma["correo"])


# ==================================================================
# VALIDACION
# ==================================================================
def validaciones(db, forma):

    cur = db.cursor()

    errors = {
        "nombre": "",
        "documento": "",
        "celular": "",
        "placa1": "",
        "placa2": "",
        "placa3": "",
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
    # placas y año de fabricacion (los 3 individualmente)
    # --------------------------------------------------------------
    acum = []
    for n in range(1, 4):
        placa = forma.get(f"placa{n}", "").upper().strip()

        if placa:
            # error: placa no cumple 6 digitos
            if len(placa) != 6:
                errors[f"placa{n}"] = "Placa invalida"

            # error: placa no cumple con minimo 2 numeros y 2 letras
            elif not re.match(
                "^(?=(?:.*[A-Za-z]){2,})(?=(?:.*\d){2,})[A-Za-z\d]{6}$", placa
            ):
                errors[f"placa{n}"] = "Placa invalida"

            # error: placa duplicada en el mismo formulario
            elif placa in acum:
                errors[f"placa{n}"] = "Placa duplicada"
            acum.append(placa)

            # error: placa inscrita por otro usuario
            cmd = """
                    SELECT 1 
                    FROM InfoPlacas 
                    WHERE 
                        Placa = ?
                        AND IdMember_FK != 0 
                        AND IdMember_FK != ? 
                    LIMIT 1
                """
            cur.execute(
                cmd,
                (placa, session["usuario"]["id_member"]),
            )
            if cur.fetchone():
                errors[f"placa{n}"] = "Placa asociada a otro usuario"

            # error: año de fabricacion no cumple formato o rango (1970 - año actual + 1)
            ano = forma.get(f"ano_fabricacion{n}")
            if ano:
                if (
                    len(ano) != 4
                    or not ano.isdigit()
                    or not (1970 <= int(ano) <= dt.now().year + 1)
                ):
                    errors[f"ano_fabricacion{n}"] = "Año de fabricación inválido"

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
    print(errors)
    return {k: v for k, v in errors.items() if v}
