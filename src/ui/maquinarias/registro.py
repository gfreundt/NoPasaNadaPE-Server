import re
from tkinter import INSERT
import uuid
from datetime import datetime as dt
from flask import current_app, request, render_template, session, redirect, url_for

from src.utils.constants import FORMATO_PASSWORD
from src.utils.utils import (
    hash_text,
    send_pushbullet,
    compare_text_to_hash,
    calcula_primera_revtec,
)
from src.comms import enviar_correo_inmediato
from src.ui.maquinarias import mis_servicios


def main():

    db = current_app.db

    # respuesta a pings para medir uptime
    if request.method == "HEAD":
        return ("", 200)

    # seguridad: evitar navegacion directa a url
    if session.get("etapa") != "registro":
        return redirect(url_for("maquinarias"))

    # Initial page load
    if request.method == "GET" or not session["usuario"].get("correo"):
        # extraer data de lo enviado al momento de la activacion y pre-llenar campos
        cursor = db.cursor()
        cmd = "SELECT Correo, NombreCompleto, TipoDocumento, NumeroDocumento, Celular FROM InfoClientesAutorizados WHERE Correo = ?"
        cursor.execute(cmd, (session["usuario"].get("correo"),))
        dato = cursor.fetchone()

        usuario = {
            "correo": dato["Correo"],
            "nombre": dato["NombreCompleto"],
            "tipo_documento": dato["TipoDocumento"],
            "numero_documento": dato["NumeroDocumento"],
            "celular": dato["Celular"],
            "placas": "",
        }

        return render_template(
            "ui-maquinarias-registro.html",
            usuario=usuario,
            password_only=session.get("password_only"),
            third_party_login=session.get("third_party_login"),
            errors={},
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
            "placa1": forma.get("placa1", "").upper().strip(),
            "placa2": forma.get("placa2", "").upper().strip(),
            "placa3": forma.get("placa3", "").upper().strip(),
            "ano_fabricacion1": forma.get("ano_fabricacion1", ""),
            "ano_fabricacion2": forma.get("ano_fabricacion2", ""),
            "ano_fabricacion3": forma.get("ano_fabricacion3", ""),
        }

        errores = validaciones(db, forma)

        if errores:
            return render_template(
                "ui-maquinarias-registro.html",
                errors=errores,
                usuario=usuario,
            )

        # No errors → proceed
        cursor = db.cursor()
        conn = db.conn
        inscribir(cursor, conn, forma)
        session["usuario"].update(usuario)
        enviar_correo_inmediato.inscripcion(
            db,
            correo=forma.get("correo"),
            nombre=forma.get("nombre"),
            placas=forma.get("placa1", "")
            + forma.get("placa2", "")
            + forma.get("placa3", ""),
        )
        session["etapa"] = "validado"
        send_pushbullet(
            title=f"NoPasaNadaPE - Usuario Inscrito ({forma.get('correo')})"
        )
        return mis_servicios.main()


# ==================================================================
# INSCRIBIR NUEVO MIEMBRO EN BASE DE DATOS
# ==================================================================


def inscribir(cursor, conn, forma):

    # extraer CodigoMiembroExterno de la informacion enviada por cliente externo
    cursor.execute(
        "SELECT CodigoClienteExterno FROM InfoClientesAutorizados WHERE Correo = ?",
        (forma["correo"],),
    )
    codigo_externo = cursor.fetchone()

    # write new record in members table and create record in last update table
    fecha_base = "2020-01-01"

    _nr = {
        "CodMemberInterno": "NPN-" + str(uuid.uuid4())[-6:].upper(),
        "CodMemberExterno": codigo_externo[0] if codigo_externo else "",
        "NombreCompleto": forma["nombre"],
        "DocTipo": forma.get("tipo_documento"),
        "DocNum": forma.get("numero_documento"),
        "Celular": forma.get("celular"),
        "Correo": forma.get("correo"),
        "LastUpdateMtcBrevetes": fecha_base,
        "LastUpdateMtcRecordsConductores": fecha_base,
        "LastUpdateSatImpuestos": fecha_base,
        "LastLoginDatetime": dt.now().strftime("%Y-%m-%d %H:%M:%S"),
        "CountFailedLogins": 0,
        "Password": hash_text(forma.get("password1")),
        "NextMessageSend": dt.now().strftime("%Y-%m-%d %H:%M:%S"),
        "NextLoginAllowed": dt.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # crear nuevo miembro
    cursor.execute(
        f"INSERT INTO InfoMiembros ({', '.join(_nr.keys())}) VALUES ({', '.join(['?'] * len(_nr))})",
        tuple(_nr.values()),
    )
    id_member = cursor.lastrowid

    # crear placas para nuevo miembro si no existe, si placa ya existe, asignar a este usuario
    for p in range(1, 4):
        placa = forma.get(f"placa{p}", "").upper().strip()
        ano_fabricacion = forma.get(f"ano_fabricacion{p}", "").strip()

        if placa:
            cursor.execute(
                """
            INSERT INTO InfoPlacas
                (IdMember_FK,
                Placa,
                AnoFabricacion,
                LastUpdateApesegSoats, 
                LastUpdateMtcRevisionesTecnicas, 
                LastUpdateSunarpFichas, 
                LastUpdateSutranMultas, 
                LastUpdateSatMultas, 
                LastUpdateCallaoMultas, 
                LastUpdateMaquinariasMantenimiento)
            VALUES (?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(Placa) DO 
                UPDATE SET  IdMember_FK = excluded.IdMember_FK,
                            AnoFabricacion = excluded.AnoFabricacion
            """,
                (
                    id_member,
                    placa,
                    ano_fabricacion,
                    fecha_base,
                    fecha_base,
                    fecha_base,
                    fecha_base,
                    fecha_base,
                    fecha_base,
                    fecha_base,
                ),
            )

            # crear manualmente el registro en DataMtcRevisionesTecnicas con la fecha calculada de vencimiento para cada placa
            # solo se hace si hay informacion de año de fabricación y si la placa no estaba antes en la tabla
            if ano_fabricacion:
                cmd = """
                        INSERT INTO DataMtcRevisionesTecnicas
                            (IdPlaca_FK, PlacaValidate, FechaHasta, FechaHastaFueCalculada)
                            SELECT ?, ?, ?, ?
                            WHERE NOT EXISTS (
                                SELECT 1
                                FROM DataMtcRevisionesTecnicas
                                WHERE PlacaValidate = ?
                            );
                      """
                cursor.execute(
                    cmd,
                    (
                        999,
                        placa,
                        calcula_primera_revtec(placa, ano_fabricacion),
                        1,
                        placa,
                    ),
                )

    conn.commit()

    session["usuario"]["id_member"] = id_member


# ==================================================================
# VALIDACIONES PARA REGISTRO Y MI PERFIL
# ==================================================================


def validaciones(db, forma, mi_perfil=False):

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
    # todos: mínimo 4 caracteres, máximo 50 caracteres
    # --------------------------------------------------------------
    if len(forma["nombre"]) < 4:
        errors["nombre"] = "Nombre debe tener un mínimo de 4 caracteres."
    elif len(forma["nombre"]) > 50:
        errors["nombre"] = "Nombre debe tener un máximo de 50 caracteres."

    # ---------------------------------------------------------------------------------
    # documento
    # registro: validar que número de documento tenga formato correcto (depende del tipo)
    #           validar que combinación tipo+numero no esté registrada
    # mi perfil: no validar porque no se puede modificar
    # ---------------------------------------------------------------------------------
    if not mi_perfil:
        if len(forma["numero_documento"]) < 5:
            errors["documento"] = "Número de documento inválido."

        if forma["tipo_documento"] == "DNI" and not re.match(
            r"^[0-9]{8}$", forma["numero_documento"]
        ):
            errors["documento"] = "DNI debe tener 8 dígitos."

        cur.execute(
            "SELECT 1 FROM InfoMiembros WHERE DocTipo = ? AND DocNum = ? LIMIT 1",
            (forma["tipo_documento"], forma["numero_documento"]),
        )
        if cur.fetchone():
            errors["documento"] = "Documento ya está asociado a otro usuario."

    # --------------------------------------------------------------
    # celular
    # todos:    debe tener 9 dígitos y solo números
    #           validar que no esté registrado por otro usuario
    # --------------------------------------------------------------
    if not re.match(r"^[0-9]{9}$", forma.get("celular", "")):
        errors["celular"] = "Celular debe tener 9 dígitos."
    else:
        cur.execute(
            """
                    SELECT 1 FROM InfoMiembros
                    WHERE Celular = ? AND Correo != ? 
                    LIMIT 1
                """,
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
                (placa, session["usuario"].get("id_member", -1)),
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

    # -------------------------------------------------------------------------------------------------
    # contraseña
    # registro: validar que contraseña cumpla formato y que password1 y password2 coincidan
    # mi perfil: validar que contraseña actual se ingreso y sea correcta y si se ingresó
    #            validar que nueva contraseña cumpla formato y que password1 y password2
    # -------------------------------------------------------------------------------------------------
    validar_nuevo_password = True

    if mi_perfil:
        current_password = forma.get("current_password")

        if current_password:  # solo si el usuario lo ingresó
            session["perfil_muestra_password"] = True

            if not compare_text_to_hash(
                text_string=current_password,
                hash_string=session["usuario"]["password"],
            ):
                errors["current_password"] = "Contraseña equivocada"
                validar_nuevo_password = False
        else:
            # mi_perfil=True pero campo vacío → no validar nada
            validar_nuevo_password = False

    if validar_nuevo_password:
        if not re.match(FORMATO_PASSWORD["regex"], forma.get("password1", "")):
            errors["password1"] = FORMATO_PASSWORD["mensaje"]
        elif forma.get("password1") != forma.get("password2"):
            errors["password2"] = "Las contraseñas no coinciden."

    # ------------------------------------------------------------------------------
    # términos y condiciones + privacidad + tratamiento de datos personales
    # registro: ambos campos deben ser "on"
    # mi perfil: no validar porque no se pueden modificar
    # -------------------------------------------------------------------------------
    if not mi_perfil and (
        forma.get("acepta_terminos") != "on" or forma.get("acepta_privacidad") != "on"
    ):
        errors["acepta_legales"] = "Es necesario aceptar ambos para poder continuar."

    # --------------------------------------------------------------
    # eliminar blancos y devolver solo errores
    # --------------------------------------------------------------
    print("--------", {k: v for k, v in errors.items() if v})
    return {k: v for k, v in errors.items() if v}
