import re
import uuid
from datetime import datetime as dt
from flask import request, render_template, session, redirect, url_for

from src.utils.utils import hash_text, send_pushbullet
from src.comms import enviar_correo_inmediato
from src.ui.maquinarias import servicios


def main(self):

    # respuesta a pings para medir uptime
    if request.method == "HEAD":
        return ("", 200)

    # seguridad: evitar navegacion directa a url
    if session.get("etapa") != "registro":
        return redirect(url_for("maquinarias"))

    # Initial page load
    if request.method == "GET" or not session["usuario"].get("correo"):

        # extraer data de lo enviado al momento de la activacion y pre-llenar campos
        cursor = self.db.cursor()
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
            "placas": forma.get("placas"),
        }

        errores = validaciones(self.db, forma)

        if errores:
            return render_template(
                "ui-maquinarias-registro.html", errors=errores, usuario=usuario
            )

        # No errors → proceed
        cursor = self.db.cursor()
        conn = self.db.conn
        inscribir(cursor, conn, forma)
        session["usuario"].update(usuario)
        enviar_correo_inmediato.inscripcion(
            self.db,
            correo=forma.get("correo"),
            nombre=forma.get("nombre"),
            placas=forma.get("placas").split(" ,"),
        )
        session["etapa"] = "validado"
        send_pushbullet(
            title=f"NoPasaNadaPE - Usuario Inscrito ({forma.get("correo")})"
        )
        return servicios.main(self)


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
        "LastUpdateSatImpuestosCodigos": fecha_base,
        "LastLoginDatetime": dt.now().strftime("%Y-%m-%d %H:%M:%S"),
        "CountFailedLogins": 0,
        "Password": hash_text(forma.get("password1")),
        "NextMessageSend": dt.now().strftime("%Y-%m-%d %H:%M:%S"),
        "NextLoginAllowed": dt.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # crear nuevo miembro
    cursor.execute(
        f"INSERT INTO InfoMiembros ({", ".join(_nr.keys())}) VALUES ({", ".join(["?"] * len(_nr))})",
        tuple(_nr.values()),
    )
    id_member = cursor.lastrowid

    # crear placas para nuevo miembro si no existe, si placa ya existe, asignar a este usuario
    for placa in forma.get("placas").split(", "):
        cursor.execute(
            """
            INSERT INTO InfoPlacas
            (IdMember_FK, Placa, LastUpdateApesegSoats, LastUpdateMtcRevisionesTecnicas, LastUpdateSunarpFichas, LastUpdateSutranMultas, LastUpdateSatMultas)
            VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(Placa) DO UPDATE SET 
            IdMember_FK = excluded.IdMember_FK
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

    session["usuario"]["id_member"] = id_member


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
    # documentos (validacion depende de tipo de documento)
    # --------------------------------------------------------------
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
    # --------------------------------------------------------------
    if not re.match(r"^[0-9]{9}$", forma.get("celular", "")):
        errors["celular"] = "Celular debe tener 9 dígitos."
    else:
        cur.execute(
            "SELECT 1 FROM InfoMiembros WHERE Celular = ? LIMIT 1", (forma["celular"],)
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
            f"SELECT 1 FROM InfoPlacas WHERE Placa IN ({", ".join(["?"] * len(_placas))}) AND IdMember_FK != 0 LIMIT 1",
            tuple(_placas),
        )

        if cur.fetchone():
            errors["placas"] = "Al menos una placa ya está inscrita por otro usuario."

    # --------------------------------------------------------------
    # password
    # --------------------------------------------------------------
    password_regex = r"^(?=.*[A-Z])(?=.*[\W_])(?=.{8,}).*$"

    if not re.match(password_regex, forma.get("password1", "")):
        errors["password1"] = (
            "Contraseña debe tener mínimo 8 caracteres, "
            "incluir una mayúscula y un carácter especial."
        )

    elif forma.get("password1") != forma.get("password2"):
        errors["password2"] = "Las contraseñas no coinciden."

    # --------------------------------------------------------------
    # términos y condiciones + privacidad
    # --------------------------------------------------------------
    if forma.get("acepta_terminos") != "on" or forma.get("acepta_privacidad") != "on":
        errors["acepta_legales"] = "Es necesario aceptar ambos para poder continuar."

    # Remove empty error fields
    final_errors = {k: v for k, v in errors.items() if v}

    return final_errors
