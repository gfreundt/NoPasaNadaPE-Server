import re
from datetime import datetime as dt, timedelta as td
from flask import render_template, redirect, request, flash, url_for

from src.comms import send_instant_email
from src.utils.utils import hash_text, compare_text_to_hash


def main(self):

    # si no hay usuario loggeado, volver a login
    if not self.session.get("loaded_user"):
        return redirect(url_for("ui-login"))

    user_session = self.session["loaded_user"]

    # ------------------------ GET ------------------------
    if request.method == "GET":

        siguiente_boletin = _compute_siguiente_boletin(user_session)

        _user = {
            "codigo": user_session["CodMember"],
            "correo": user_session["Correo"],
            "dni": user_session["DocNum"],
            "nombre": user_session["NombreCompleto"],
            "celular": user_session["Celular"],
        }

        return render_template(
            "cuenta-mis-datos.html",
            user=_user,
            placas=user_session["Placas"],
            sgte_boletin=siguiente_boletin,
            errors={},
        )

    # ------------------------ POST ------------------------
    form_response = dict(request.form)

    # --- eliminar cuenta ---
    if "eliminar" in form_response:
        _delete_user(self, user_session)
        return redirect("logout")

    # --- detectar cambios ---
    current_placas = list(user_session["Placas"].values())
    changes_made = validation_changes(
        user=user_session,
        placas=current_placas,
        post=form_response,
    )

    siguiente_boletin = _compute_siguiente_boletin(user_session)

    # --- si NO hubo cambios ---
    if not changes_made:
        flash("No se realizaron cambios.", "warning")
        return redirect("mis-datos")

    # --- validar cambios ---
    errors = validation(form_response, db=self.db)
    if any(errors.values()):
        _user = {
            "codigo": user_session["CodMember"],
            "correo": user_session["Correo"],
            "dni": user_session["DocNum"],
            "nombre": form_response["nombre"],
            "celular": form_response["celular"],
        }
        placas_form = {
            "placa1": form_response["placa1"],
            "placa2": form_response["placa2"],
            "placa3": form_response["placa3"],
        }

        return render_template(
            "cuenta-mis-datos.html",
            user=_user,
            placas=placas_form,
            sgte_boletin=siguiente_boletin,
            errors=errors,
        )

    # --- aplicar cambios (sin errores) ---
    _apply_user_changes(self, user_session, form_response, changes_made)

    flash(changes_made, "success")
    return redirect("mis-datos")


# ============================================================
# --------------------- HELPERS ------------------------------
# ============================================================


def _compute_siguiente_boletin(user):
    """Calcula fecha + días restantes para mostrar en UI"""
    if user["NextMessageSend"]:
        fecha = dt.strptime(user["NextMessageSend"], "%Y-%m-%d %H:%M:%S")
        return {
            "fecha": user["NextMessageSend"][:10],
            "dias": (fecha - dt.now()).days + 1,
        }
    else:
        mañana = dt.now() + td(days=1)
        return {"fecha": mañana.strftime("%Y-%m-%d"), "dias": 1}


def _delete_user(self, user):
    """Elimina usuario y placas asociadas"""
    cur = self.db.cursor()

    # copiar, borrar, soltar placas
    cur.execute(
        "INSERT INTO InfoMiembrosInactivos SELECT * FROM InfoMiembros WHERE IdMember = ?",
        (user["IdMember"],),
    )
    cur.execute("DELETE FROM InfoMiembros WHERE IdMember = ?", (user["IdMember"],))
    cur.execute(
        "UPDATE InfoPlacas SET IdMember_FK = 0 WHERE IdMember_FK = ?",
        (user["IdMember"],),
    )
    self.db.commit()

    # enviar correo
    send_instant_email.send_cancel(
        correo=user["Correo"],
        nombre=user["NombreCompleto"],
    )

    self.log(
        message=f"Eliminado {user['CodMember']} | {user['NombreCompleto']} | {user['DocNum']} | {user['Correo']}"
    )
    flash("Usuario eliminado.", "success")


def _apply_user_changes(self, user, form, changes_made):
    cur = self.db.cursor()

    # actualizar info básica
    next_msg = None
    if "Placas" in changes_made:
        next_msg = (dt.now() + td(hours=2)).strftime("%Y-%m-%d %H:%M:%S")

    cur.execute(
        """UPDATE InfoMiembros
           SET NombreCompleto = ?, DocNum = ?, Celular = ?, NextMessageSend = COALESCE(?, NextMessageSend)
           WHERE IdMember = ?""",
        (form["nombre"], form["dni"], form["celular"], next_msg, user["IdMember"]),
    )

    # actualizar contraseña
    if "Contraseña" in changes_made:
        cur.execute(
            "UPDATE InfoMiembros SET Password = ? WHERE IdMember = ?",
            (hash_text(form["contra2"]), user["IdMember"]),
        )

    # reset placas
    cur.execute(
        "UPDATE InfoPlacas SET IdMember_FK = 0 WHERE IdMember_FK = ?",
        (user["IdMember"],),
    )

    # volver a asignar placas
    nuevas_placas = [
        p.strip().upper()
        for p in (form["placa1"], form["placa2"], form["placa3"])
        if p.strip()
    ]

    for placa in nuevas_placas:
        cur.execute("SELECT IdPlaca FROM InfoPlacas WHERE Placa = ?", (placa,))
        row = cur.fetchone()

        if row:
            cur.execute(
                "UPDATE InfoPlacas SET IdMember_FK = ? WHERE Placa = ?",
                (user["IdMember"], placa),
            )
        else:
            cur.execute("SELECT COALESCE(MAX(IdPlaca), 0) + 1 FROM InfoPlacas")
            next_id = cur.fetchone()[0]

            default_date = "2020-01-01"
            cur.execute(
                """INSERT INTO InfoPlacas
                   (IdPlaca, IdMember_FK, Placa, Fecha1, Fecha2, Fecha3, Fecha4, Fecha5)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    next_id,
                    user["IdMember"],
                    placa,
                    default_date,
                    default_date,
                    default_date,
                    default_date,
                    default_date,
                ),
            )

    self.db.commit()

    # update session to match DB
    user["NombreCompleto"] = form["nombre"]
    user["Celular"] = form["celular"]
    user["DocNum"] = form["dni"]
    user["Placas"] = {f"placa{i+1}": p for i, p in enumerate(nuevas_placas)}


# ============================================================
# ---------------------- VALIDADORES --------------------------
# ============================================================


def validation(form_response, db):
    errors = {
        "placa1": [],
        "placa2": [],
        "placa3": [],
        "dni": [],
        "nombre": [],
        "celular": [],
        "contra1": [],
        "contra2": [],
        "contra3": [],
    }

    cur = db.cursor()

    # nombre
    if len(form_response["nombre"]) < 5:
        errors["nombre"].append("Nombre debe tener mínimo 5 letras")

    # celular
    if not re.match(r"^[0-9]{9}$", form_response["celular"]):
        errors["celular"].append("Ingrese un celular válido")
    else:
        cur.execute(
            """SELECT 1 FROM InfoMiembros
               WHERE Celular = ? AND IdMember != (SELECT IdMember FROM InfoMiembros WHERE DocNum = ?)""",
            (form_response["celular"], form_response["dni"]),
        )
        if cur.fetchone():
            errors["celular"].append("Celular ya está asociado con otra cuenta.")

    # placas
    for p in range(1, 3 + 1):
        idx = f"placa{p}"
        val = form_response[idx].strip().upper()

        if val and not re.match(r"^(?=.*\d)[A-Z0-9]{6}$", val):
            errors[idx].append("Usar un formato válido")
        else:
            cur.execute(
                """SELECT 1 FROM InfoPlacas
                   WHERE Placa = ? AND IdMember_FK != 0
                         AND IdMember_FK != (SELECT IdMember FROM InfoMiembros WHERE DocNum = ?)""",
                (val, form_response["dni"]),
            )
            if cur.fetchone():
                errors[idx].append("Placa ya está asociada con otra cuenta.")

    # contraseña
    if len(form_response["contra1"]) > 0:
        cur.execute(
            "SELECT Password FROM InfoMiembros WHERE Correo = ?",
            (form_response["correo"],),
        )
        stored = cur.fetchone()[0]

        if not compare_text_to_hash(form_response["contra1"], stored):
            errors["contra1"].append("Contraseña equivocada")

        elif not re.match(r"^(?=.*[A-Z])(?=.*\d).{6,20}$", form_response["contra2"]):
            errors["contra2"].append("Mínimo 6 caracteres, incluir mayúscula y número")

        elif form_response["contra2"] != form_response["contra3"]:
            errors["contra3"].append("Contraseñas no coinciden")

    return errors


def validation_changes(user, placas, post):
    changes = ""

    if user["NombreCompleto"] != post["nombre"]:
        changes += "Nombre actualizado. "

    if user["Celular"] != post["celular"]:
        changes += "Celular actualizado. "

    nuevas = sorted([p for p in (post["placa1"], post["placa2"], post["placa3"]) if p])
    actuales = sorted(placas)

    if nuevas != actuales:
        changes += "Placas actualizadas. "

    if post["contra1"] and post["contra2"] != user["Password"]:
        changes += "Contraseña actualizada. "

    return changes
