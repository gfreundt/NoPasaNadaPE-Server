import re


class FormValidate:

    def __init__(self, db):

        self.conn = db.conn
        self.cursor = db.cursor

        self.load_members()

    def load_members(self):
        cmd = "SELECT * FROM InfoMiembros"
        self.cursor.execute(cmd)
        self.user_db = self.cursor.fetchall()
        self.dnis = [i[4] for i in self.user_db]
        self.celulares = [str(i[5]) for i in self.user_db]
        self.correos = [i[6] for i in self.user_db]

    def login(self, form_data, db):

        # check if correo exists
        cmd = f"SELECT * FROM InfoMiembros WHERE Correo = '{form_data["correo"]}'"
        self.cursor.execute(cmd)
        if not self.cursor.fetchone():
            return {"correo": ["Correo no registrado"]}

        # check if password correct for that correo
        cmd += f" AND Password = '{form_data["password"]}'"
        self.cursor.execute(cmd)
        if not self.cursor.fetchone():
            return {"password": ["Contraseña equivocada"]}

        # correo/password combo correct
        return False

    def reg(self, attempt, page, codigo=None):

        # realizar todas las validaciones
        errors = {
            "nombre": [],
            "dni": [],
            "correo": [],
            "celular": [],
            "codigo": [],
            "password1": [],
            "password2": [],
        }

        if page == 1:

            # nombre
            if len(attempt["nombre"]) < 5:
                errors["nombre"].append("Nombre debe tener mínimo 5 letras")

            # dni
            if not re.match(r"^[0-9]{8}$", attempt["dni"]):
                errors["dni"].append("DNI solamente debe tener 8 dígitos")
            if attempt["dni"] in self.dnis:
                errors["dni"].append("DNI ya está registado")

            # correo
            if not re.match(
                r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", attempt["correo"]
            ):
                errors["correo"].append("Ingrese un correo válido")
            if attempt["correo"] in self.correos:
                errors["correo"].append("Correo ya está registrado")

            # celular
            if not re.match(r"^[0-9]{9}$", attempt["celular"]):
                errors["celular"].append("Ingrese un celular válido")
            if attempt["celular"] in self.celulares:
                errors["celular"].append("Celular ya esta registrado")

        elif page == 2:

            # codigo
            if not re.match(r"^[A-Za-z]{4}$", attempt["codigo"]):
                errors["codigo"].append("Codigo de validacion son 4 letras")
            if attempt["codigo"] != codigo:
                errors["codigo"].append("Código de validación incorrecto")

            # constraseña
            if not re.match(r"^(?=.*[A-Z])(?=.*\d).{6,20}$", attempt["password1"]):
                errors["password1"].append(
                    "Al menos 6 caracteres e incluir una mayúscula y un número"
                )

            # validacion de contraseña
            if attempt["password1"] != attempt["password2"]:
                errors["password2"].append("Contraseñas no coinciden")

        return errors

    def mic(self, mic):

        # realizar todas las validaciones
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

        # nombre
        if len(mic["nombre"]) < 5:
            errors["nombre"].append("Nombre debe tener mínimo 5 letras")

        # celular: formato correcto (9 digitos)
        if not re.match(r"^[0-9]{9}$", mic["celular"]):
            errors["celular"].append("Ingrese un celular válido")

        # celular: no se esta duplicando con otro celular de la base de datos (no necesario revisar si hay error previo)
        else:
            self.cursor.execute(
                f"SELECT Celular FROM InfoMiembros WHERE Celular = '{mic["celular"]}' AND IdMember != (select IdMember FROM InfoMiembros WHERE DocNum='{mic["dni"]}')"
            )
            if self.cursor.fetchone():
                errors["celular"].append("Celular ya está asociado con otra cuenta.")

        # placas
        for p in range(1, 4):

            _index = f"placa{p}"

            # dos letras y cuatro números, o tres letras y tres números, sin guion
            if mic[_index] and not re.match(r"^[A-Z][A-Z0-9]{2}\d{3}$", mic[_index]):
                errors[_index].append("Usar un formato válido")

            # no se esta duplicando con otra placa de la base de datos (no necesario revisar si hay error previo)
            else:
                self.cursor.execute(
                    f"SELECT Placa FROM InfoPlacas WHERE Placa = '{mic[_index]}' AND IdMember_FK != 0 AND IdMember_FK != (select IdMember FROM InfoMiembros WHERE DocNum='{mic["dni"]}')"
                )
                if self.cursor.fetchone():
                    errors[_index].append("Placa ya está asociada con otra cuenta.")

        # revisar solo si se ingreso algo en el campo de contraseña actual
        if len(mic["contra1"]) > 0:

            # contraseña actual
            self.cursor.execute(
                f"SELECT Password FROM InfoMiembros WHERE Correo = '{mic["correo"]}'"
            )
            _password = self.cursor.fetchone()[0]

            if _password != str(mic["contra1"]):
                errors["contra1"].append("Contraseña equivocada")

            # contraseña nueva
            elif not re.match(r"^(?=.*[A-Z])(?=.*\d).{6,20}$", mic["contra2"]):
                errors["contra2"].append(
                    "Mínimo 6 caracteres, incluir mayúscula y número"
                )

            # validacion de nueva contraseña
            elif mic["contra2"] != mic["contra3"]:
                errors["contra3"].append("Contraseñas no coinciden")

        return errors

    def mic_changes(self, user, placas, post):

        changes = ""

        # nombre ha cambiado
        if user[2] != post["nombre"]:
            changes += "Nombre actualizado. "

        # celular ha cambiado
        if user[5] != post["celular"]:
            changes += "Celular actualizado. "

        # alguna placa ha cambiado
        if sorted(
            [i for i in (post["placa1"], post["placa2"], post["placa3"]) if i]
        ) != sorted(placas):
            changes += "Placas actualizadas. "

        # contraseña ha cambiado
        if len(post["contra1"]) > 0 and str(post["contra2"]) != user[11]:
            changes += "Contraseña actualizada. "

        return changes

    def update_password(self, correo, password, db):
        cmd = (
            f"UPDATE InfoMiembros SET Password = '{password}' WHERE Correo = '{correo}'"
        )
        db.cursor.execute(cmd)
        db.conn.commit()
