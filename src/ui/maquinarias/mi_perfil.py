import re
from flask import current_app, redirect, request, render_template, url_for, session

from src.ui.maquinarias import login
from src.utils.utils import hash_text, calcula_primera_revtec
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
        forma = request.form.to_dict(flat=True)

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

        print("*****", usuario)

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
        ano_fabricacion = forma.get(f"ano_fabricacion{k}")
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
                UPDATE SET  IdMember_FK = excluded.IdMember_FK,
                            AnoFabricacion = excluded.AnoFabricacion
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
                ano_fabricacion,
            ),
        )

        #
        insertar_fechahasta_revtec(cursor, placa, ano_fabricacion)

    conn.commit()

    # volver a extraer data de usuario para actualizar session con nuevos datos
    login.extraer_data_usuario(cursor, correo=forma["correo"])


def insertar_fechahasta_revtec(cursor, placa, ano_fabricacion):
    """
    Calcula FechaHasta en DataMtcRevisionesTecnicas usando tabla del MTC si no hay data previa
    Casos que no sean cubiertos por esta logica se actualizaran en Mantenimiento
    """

    placa = placa.upper()

    # caso A: usuario no ingreso año de fabricacion
    if not ano_fabricacion:
        # FechaHasta fue extraida previamente --> no hacer nada
        # FechaHasta fue calculada previamente --> eliminar FechaHasta y resetear flag de calculada
        cmd = """
                    UPDATE DataMtcRevisionesTecnicas
                       SET FechaHasta = NULL,
                           FechaHastaFueCalculada = 0
                    WHERE  PlacaValidate = ?
                      AND  FechaHastaFueCalculada = 1
                """
        cursor.execute(cmd, (placa,))
        return

    # caso B: usuario si ingreso año de fabricacion
    cmd = """   
            SELECT 1
            FROM DataMtcRevisionesTecnicas
            WHERE PlacaValidate = ?
            """
    cursor.execute(cmd, (placa.upper(),))
    resultado = cursor.fetchone()

    # caso B1: no existe la placa en DataMtcRevisionesTecnicas --> crearla y calcular FechaHasta con nuevo año de fabricacion
    if not resultado:
        cmd = """
                INSERT INTO DataMtcRevisionesTecnicas
                       (IdPlaca_FK, PlacaValidate, FechaHasta, FechaHastaFueCalculada)
                       VALUES (?, ?, ?, 1)
                """
        cursor.execute(
            cmd, (999, placa, calcula_primera_revtec(placa, ano_fabricacion))
        )
        return

    # caso B2: si existe la placa en DataMtcRevisionesTecnicas
    # tiene FechaHasta extraida --> ignorar
    # tiene FechaHasta calculada --> recalcular FechaHasta con nuevo año de fabricacion
    cmd = """
                UPDATE DataMtcRevisionesTecnicas
                    SET   FechaHasta = ?,
                          FechaHastaFueCalculada = 1
                    WHERE PlacaValidate = ?
                      AND FechaHastaFueCalculada = 1
                """
    cursor.execute(cmd, (calcula_primera_revtec(placa, ano_fabricacion), placa))
    return
