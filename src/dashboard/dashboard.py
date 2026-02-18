from flask import render_template, jsonify, redirect, request
import threading
import logging
from copy import deepcopy as copy
from datetime import datetime as dt, timedelta as td
from collections import deque
from src.dashboard import cron
from src.utils.constants import TABLAS_BD
from src.utils.utils import get_public_ip, get_local_ip
from security.keys import DASHBOARD_URL

from pprint import pprint


logger = logging.getLogger(__name__)


class Dashboard:
    def __init__(self, db, soy_master):
        self.db = db
        self.master = soy_master
        self.state_file = "dashboard_state.json"

        # crear estrcutura de variables y valores iniciales
        self.set_initial_data()

        # iniciar cron (procesos automaticos que corren cada cierto plazo) solo si es worker "master"
        if self.master:
            logger.info("Iniciando cron en worker master")
            print(f" > DASHBOARD: http://{get_local_ip()}:5000/{DASHBOARD_URL}")
            cron.main(self)

    def set_server(self, server_instance):
        self.server = server_instance

    def set_initial_data(self):
        self.vpn_location = ""
        self.log_entries = deque(maxlen=35)
        self.assigned_cards = []
        self.config_autoscraper = True
        self.config_automensaje = False
        self.config_enviar_pushbullet = False
        self.config_obligar_vpn = True
        self.siguiente_autoscraper = dt.now() + td(minutes=5)
        self.scrapers_corriendo = False

        self.ip_original, _ = get_public_ip()

        _empty_card = {
            "title": "No Asignado",
            "progress": 0,
            "msg": [],
            "status": 0,
            "text": "Inactivo",
            "lastUpdate": "Pendiente",
        }
        self.data = {
            "activities": "",
            "top_left": "No Pasa Nada Dashboard",
            "top_right": {"content": "Inicializando...", "status": 0},
            "cards": [copy(_empty_card) for _ in range(32)],
            "bottom_left": [],
            "bottom_right": [],
            "scrapers_kpis": {
                key: {
                    "status": "INACTIVO",
                    "pendientes": "",
                    "eta": "",
                    "threads_activos": "",
                    "alertas": "",
                    "boletines": "",
                }
                for key in TABLAS_BD
            }
            | {"Acumulado": {}},
            "scrapers_en_linea": {key: True for key in TABLAS_BD},
        }

    # def log(self, **kwargs):

    #     if "general_status" in kwargs:
    #         self.data["top_right"]["content"] = kwargs["general_status"][0]
    #         self.data["top_right"]["status"] = kwargs["general_status"][1]

    #     if "action" in kwargs:
    #         _ft = f"{dt.now():%Y-%m-%d %H:%M:%S} > {kwargs['action']}"
    #         self.log_entries.append(_ft)
    #         self.data["bottom_left"].append(_ft[:140])
    #         self.data["bottom_left"] = self.data["bottom_left"][-40:]

    #     if "card" in kwargs:
    #         for field in kwargs:
    #             if field == "card":
    #                 continue
    #             self.data["cards"][kwargs["card"]][field] = kwargs[field]

    #     if "usuario" in kwargs:
    #         _ft = f"<b>{dt.now():%Y-%m-%d %H:%M:%S} ></b>{kwargs['usuario']}"
    #         self.data["bottom_left"].append(_ft[:140])
    #         if len(self.data["bottom_left"]) > 30:
    #             self.data["bottom_left"].pop(0)

    #     # manejar gunicorn workers paralelos
    #     if self.master:
    #         with open(self.state_file, "w") as f:
    #             json.dump(self.data, f)

    # -------- ACCION DE URL DE INGRESO --------
    def dashboard(self):
        # Pass configuration variables and next run time to the template
        return render_template(
            "dashboard.html",
            config_autoscraper=self.config_autoscraper,
            config_automensaje=self.config_automensaje,
            config_enviar_pushbullet=self.config_enviar_pushbullet,
            siguiente_autoscraper=(
                self.siguiente_autoscraper.strftime("%H:%M:%S")
                if self.config_autoscraper
                else None
            ),
            data=self.data,
        )

    # ------- ACCIONES DE APIS (INTERNO) -------
    def get_data(self):
        if not self.master:
            try:
                with open(self.state_file, "r") as f:
                    return f.read(), 200, {"Content-Type": "application/json"}
            except Exception:
                return jsonify({"error": "Master no iniciado"}), 503

        # Master returns from its own live memory
        with self.server.data_lock:
            return jsonify(self.data)

    # -------- ACCIONES DE BOTONES ----------
    def datos_alerta(self):
        pass

    def datos_boletin(self):
        pass

    def actualizar_alertas(self):
        pass

    def actualizar_boletines(self):
        pass

    def generar_alertas(self):
        pass

    def generar_boletines(self):
        pass

    def enviar_mensajes(self):
        pass

    def toggle_scraper_status(self):
        """
        Recibe una solicitud POST desde el frontend para cambiar el estado 'En Linea'
        de un scraper específico (True/False).
        """
        data = request.get_json()
        service = data.get("service")
        is_checked = data.get("checked")

        # Utilizamos _ALL_SERVICES para validar que el servicio sea conocido
        if service and service in TABLAS_BD:
            with self.server.data_lock:
                self.data["scrapers_en_linea"][service] = is_checked
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Invalid service"}), 400

    def clear_logs(self):
        self.log_entries.clear()
        self.data["bottom_left"].clear()
        return redirect("/")

    def db_vacuum(self):
        logger.info("Iniciando VACUUM de la base de datos.")
        return redirect("/")

    def hacer_tests(self):
        try:
            tests.main(self)
        except KeyboardInterrupt:
            pass
        return redirect("/")

    def db_info(self):
        logger.info("Solicitud de información de la base de datos recibida.")

        cursor = self.db.cursor()

        # obtener info de autorizados
        cursor.execute("SELECT * FROM InfoClientesAutorizados")
        n = cursor.fetchall()
        n = [dict(row) for row in n]

        # obtener info de miembros
        cursor.execute("SELECT * FROM InfoMiembros")
        m = cursor.fetchall()
        m = [dict(row) for row in m]

        # obtener info de placas
        cursor.execute("SELECT * FROM InfoPlacas")
        p = cursor.fetchall()
        p = [dict(row) for row in p]

        # obtener mensajes enviados
        cursor.execute(
            "SELECT * FROM StatusMensajesEnviados ORDER BY FechaEnvio DESC LIMIT 50"
        )
        s = cursor.fetchall()
        s = [dict(row) for row in s]

        return jsonify(
            {"miembros": m, "placas": p, "autorizados": n, "mensajes(50)": s}
        )

    def toggle_config(self):
        """
        Recibe una solicitud POST desde el frontend para cambiar el estado de las
        configuraciones principales (Autoscraper, Automensajes, Pushbullet).
        """
        if not request.is_json:
            return jsonify({"success": False, "error": "Missing JSON in request"}), 400

        data = request.get_json()

        # Expects a single key/value pair, e.g., {"autoscraper": True}
        for key, new_status in data.items():
            # Validate the key and ensure the status is a boolean
            if key in [
                "autoscraper",
                "automensaje",
                "enviar_pushbullet",
            ] and isinstance(new_status, bool):
                attr_name = f"config_{key}"

                with self.server.data_lock:
                    # Use setattr to dynamically update the class attribute
                    setattr(self, attr_name, new_status)

                return (
                    jsonify(
                        {"success": True, "message": f"{key} updated successfully."}
                    ),
                    200,
                )

        return (
            jsonify({"success": False, "error": "Invalid configuration key or status"}),
            400,
        )

    def actualizar_logs(self):
        return redirect("/")

    def db_completa(self):
        return redirect("/")

    def actualizar_de_json(self):
        return redirect("/")

    def log_get(self):
        return redirect("/")

    def run_in_background(self):
        flask_thread = threading.Thread(target=self.run, daemon=True)
        flask_thread.start()
        return flask_thread

    def runx(self):
        print("MONITOR RUNNING ON: http://localhost:7400/")
        self.app.run(debug=False, threaded=True, host="0.0.0.0", port=7400)
