from flask import Flask, render_template, jsonify, redirect, request, url_for
import threading
import logging
from copy import deepcopy as copy
import os
from datetime import datetime as dt, timedelta as td
import requests
import json
from collections import deque
from src.dashboard import cron
from src.utils.constants import (
    NETWORK_PATH,
    TABLAS_BD,
)
from src.updates import gather_all
from src.dashboard import update_kpis
from src.updates import datos_actualizar
from src.comms import generar_mensajes, enviar_correo_mensajes
from src.utils.utils import get_public_ip
from pprint import pprint


logging.getLogger("werkzeug").disabled = True


class Dashboard:
    def __init__(self, db, soy_master):
        self.db = db
        self.master = soy_master
        self.state_file = "dashboard_state.json"

        # temporal

        cursor = db.cursor()
        cursor.execute(
            "DELETE FROM InfoPlacas WHERE IdMember_FK = (SELECT IdMember FROM InfoMiembros WHERE Correo ='gabfre@gmail.com')"
        )
        cursor.execute("DELETE FROM InfoMiembros WHERE Correo = 'gabfre@gmail.com'")

        #

        # crear estrcutura de variables y valores iniciales
        self.set_initial_data()
        self.log(action=f"Original IP: {self.original_ip}")

        # iniciar cron (procesos automaticos que corren cada cierto plazo) solo si es worker "master"
        if self.master:
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

        self.original_ip = get_public_ip()

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

    def log(self, **kwargs):

        if "general_status" in kwargs:
            self.data["top_right"]["content"] = kwargs["general_status"][0]
            self.data["top_right"]["status"] = kwargs["general_status"][1]

        if "action" in kwargs:
            _ft = f"{dt.now():%Y-%m-%d %H:%M:%S} > {kwargs["action"]}"
            self.log_entries.append(_ft)
            self.data["bottom_left"].append(_ft[:140])

        if "card" in kwargs:
            for field in kwargs:
                if field == "card":
                    continue
                self.data["cards"][kwargs["card"]][field] = kwargs[field]

        if "usuario" in kwargs:
            _ft = f"<b>{dt.now():%Y-%m-%d %H:%M:%S} ></b>{kwargs["usuario"]}"
            self.data["bottom_left"].append(_ft[:140])
            if len(self.data["bottom_left"]) > 30:
                self.data["bottom_left"].pop(0)

        # manejar gunicorn workers paralelos
        if self.master:
            with open(self.state_file, "w") as f:
                json.dump(self.data, f)

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
        # """
        # endpoint for dashboard to update continually on dashboard information:
        # sends back a dictionary (self.data)
        # """
        # with self.server.data_lock:
        #     return jsonify(self.data)

    # -------- ACCIONES DE BOTONES ----------
    def datos_alerta(self):
        # solicitar actualizacion a servidor
        self.actualizar_datos_alertas = datos_actualizar.alertas(self)
        return redirect(url_for("dashboard"))

    def datos_boletin(self):
        # solicitar actualizacion a servidor
        self.actualizar_datos_boletines = datos_actualizar.boletines(self)
        return redirect(url_for("dashboard"))

    def actualizar_alertas(self):
        # logica general de scrapers
        all_updates = self.actualizar_datos_alertas
        tamano_actualizacion = gather_all.gather_threads(
            dash=self, all_updates=all_updates
        )
        self.log(
            action=f"[ ACTUALIZACION ALERTAS ] Tamaño: {tamano_actualizacion} kB",
        )
        return redirect(url_for("dashboard"))

    def actualizar_boletines(self):
        # logica general de scrapers
        all_updates = self.actualizar_datos_boletines
        tamano_actualizacion = gather_all.gather_threads(
            dash=self, all_updates=all_updates
        )

        self.log(
            action=f"[ ACTUALIZACION BOLETINES ] Tamaño: {tamano_actualizacion} kB",
        )
        return redirect(url_for("dashboard"))

    def generar_alertas(self):
        # genera todas las alertas que tocan y las guarda en "alertas_pendientes.json"
        mensajes = generar_mensajes.alertas(db=self.db)
        if len(mensajes) > 0:
            self.log(action=f"[ CREAR ALERTAS ] Total: {len(mensajes)}")

        # mantenerse en la misma pagina
        return redirect(url_for("dashboard"))

    def generar_boletines(self):
        # genera todos los boletines que tocan y los guarda en "boletines_pendientes.json"
        mensajes = generar_mensajes.boletines(db=self.db)
        if len(mensajes) > 0:
            self.log(action=f"[ CREAR BOLETINES ] Total: {len(mensajes)}")

        # mantenerse en la misma pagina
        return redirect(url_for("dashboard"))

    def enviar_mensajes(self):
        # envia todos los mensajes pendientes en "alertas_pendientes.json" y "boletines_pendientes.json"
        mensajes = enviar_correo_mensajes.send(db=self.db)
        if mensajes["ALERTA"] != 0 or mensajes["BOLETIN"] != 0:
            self.log(
                action=f"[ ENVIAR MENSAJES ] Alertas: {mensajes["ALERTA"]} | Boletines: {mensajes["BOLETIN"]}"
            )

        # mantenerse en la misma pagina
        return redirect(url_for("dashboard"))

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
            self.log(
                action=f"[ CONFIG ] Scraper {service} toggled {'ON' if is_checked else 'OFF'}"
            )
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Invalid service"}), 400

    def clear_logs(self):
        self.log_entries.clear()
        self.data["bottom_left"].clear()
        return redirect("/")

    def db_vacuum(self):

        return redirect("/")

    def hacer_tests(self):
        try:
            tests.main(self)
        except KeyboardInterrupt:
            self.log(action="*** Cannot execute test (server offline?)")
        return redirect("/")

    def db_info(self):
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM InfoMiembros")
        m = cursor.fetchall()
        m = [dict(row) for row in m]
        cursor.execute("SELECT * FROM InfoPlacas")
        p = cursor.fetchall()
        p = [dict(row) for row in p]

        return jsonify({"miembros": m, "placas": p})

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

                self.log(
                    action=f"[ CONFIG ] {key.capitalize()} toggled {'ON' if new_status else 'OFF'}"
                )
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


"""
from flask import Flask, render_template, jsonify, redirect, request, url_for
import threading
import logging
from copy import deepcopy as copy
import os
import fcntl  # Necessary for system-level locking
from datetime import datetime as dt, timedelta as td
import requests
import json
from collections import deque
from src.dashboard import cron
from src.utils.constants import (
    NETWORK_PATH,
    TABLAS_BD,
)
from src.updates import gather_all
from src.dashboard import update_kpis
from src.updates import datos_actualizar
from src.comms import generar_mensajes, enviar_correo_mensajes
from pprint import pprint

logging.getLogger("werkzeug").disabled = True

class Dashboard:
    def __init__(self, db, soy_master):
        self.db = db
        # Shared file where the Master worker will save the 'live' data
        self.state_file = "dashboard_state.json"
        
        # --- MASTER ELECTION VIA FILE LOCK ---
        # We ignore the 'soy_master' flag from Gunicorn and let the OS decide.
        # This ensures exactly ONE worker runs the background logic.
        self.lock_file = open("dashboard_master.lock", "w")
        try:
            # LOCK_EX: Exclusive lock
            # LOCK_NB: Non-blocking (fails if another worker already has it)
            fcntl.flock(self.lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.master = True
            print(f"Process {os.getpid()} ACQUIRED lock. Acting as MASTER.")
        except IOError:
            self.master = False
            print(f"Process {os.getpid()} lock busy. Acting as WORKER/SLAVE.")

        # Initialize local structure
        self.set_initial_data()

        # Only the actual lock-holder starts the background cron processes
        if self.master:
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

    def persist_state(self):
        if self.master:
            try:
                with open(self.state_file, "w") as f:
                    json.dump(self.data, f)
            except Exception as e:
                print(f"Error persisting state: {e}")

    def log(self, **kwargs):
        if "general_status" in kwargs:
            self.data["top_right"]["content"] = kwargs["general_status"][0]
            self.data["top_right"]["status"] = kwargs["general_status"][1]

        if "action" in kwargs:
            _ft = f"{dt.now():%Y-%m-%d %H:%M:%S} > {kwargs['action']}"
            self.log_entries.append(_ft)
            self.data["bottom_left"].append(_ft[:140])

        if "card" in kwargs:
            for field in kwargs:
                if field == "card":
                    continue
                self.data["cards"][kwargs["card"]][field] = kwargs[field]

        if "usuario" in kwargs:
            _ft = f"<b>{dt.now():%Y-%m-%d %H:%M:%S} ></b>{kwargs['usuario']}"
            self.data["bottom_left"].append(_ft[:140])
            if len(self.data["bottom_left"]) > 30:
                self.data["bottom_left"].pop(0)
        
        # Every time Master logs an update, broadcast it to the shared file
        self.persist_state()

    def dashboard(self):
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

    def get_data(self):
        if not self.master:
            if os.path.exists(self.state_file):
                try:
                    with open(self.state_file, "r") as f:
                        return jsonify(json.load(f))
                except Exception:
                    pass # Fallback to local memory if file is being written
        
        with self.server.data_lock:
            return jsonify(self.data)

    def toggle_config(self):
        if not request.is_json:
            return jsonify({"success": False, "error": "Missing JSON"}), 400

        data = request.get_json()
        for key, new_status in data.items():
            if key in ["autoscraper", "automensaje", "enviar_pushbullet"] and isinstance(new_status, bool):
                attr_name = f"config_{key}"
                
                with self.server.data_lock:
                    setattr(self, attr_name, new_status)

                # Log the change (Master will persist this to the JSON)
                self.log(action=f"[ CONFIG ] {key.capitalize()} toggled {'ON' if new_status else 'OFF'}")
                return jsonify({"success": True, "message": f"{key} updated."}), 200

        return jsonify({"success": False, "error": "Invalid key"}), 400

    # ... [Rest of the helper methods remain unchanged] ...
    def datos_alerta(self):
        self.actualizar_datos_alertas = datos_actualizar.alertas(self)
        return redirect(url_for("dashboard"))

    def datos_boletin(self):
        self.actualizar_datos_boletines = datos_actualizar.boletines(self)
        return redirect(url_for("dashboard"))

    def actualizar_alertas(self):
        all_updates = self.actualizar_datos_alertas
        tamano_actualizacion = gather_all.gather_threads(dash=self, all_updates=all_updates)
        self.log(action=f"[ ACTUALIZACION ALERTAS ] Tamaño: {tamano_actualizacion} kB")
        return redirect(url_for("dashboard"))

    def toggle_scraper_status(self):
        data = request.get_json()
        service = data.get("service")
        is_checked = data.get("checked")
        if service and service in TABLAS_BD:
            with self.server.data_lock:
                self.data["scrapers_en_linea"][service] = is_checked
            self.log(action=f"[ CONFIG ] Scraper {service} toggled {'ON' if is_checked else 'OFF'}")
            return jsonify({"success": True})
        return jsonify({"success": False}), 400

    def clear_logs(self):
        self.data["bottom_left"].clear()
        self.persist_state()
        return redirect("/")

    def run_in_background(self):
        flask_thread = threading.Thread(target=self.run, daemon=True)
        flask_thread.start()
        return flask_thread




from flask import Flask, render_template, jsonify, redirect, request, url_for
import threading
import logging
import os
import fcntl
import json
from copy import deepcopy as copy
from datetime import datetime as dt, timedelta as td
from collections import deque
from src.dashboard import cron

# ... keep your existing imports ...

class Dashboard:
    def __init__(self, db, soy_master):
        self.db = db
        self.state_file = "dashboard_state.json"
        
        # --- EFFICIENT MASTER ELECTION ---
        self.lock_file = open("dashboard_master.lock", "w")
        try:
            fcntl.flock(self.lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.master = True
        except IOError:
            self.master = False

        # Initialize structure
        self.set_initial_data()

        # ONLY the master worker consumes CPU/Memory for the background loop
        if self.master:
            print(">>> MASTER WORKER STARTING BACKGROUND TASKS")
            cron.main(self)
        else:
            # Slaves do nothing upon initialization to save resources
            pass

    def set_initial_data(self):
        # ... keep your existing set_initial_data code here ...
        # (This defines the dictionary structure)
        pass

    def persist_state(self):
        if self.master:
            with open(self.state_file, "w") as f:
                json.dump(self.data, f)

    def log(self, **kwargs):
        # ... your existing log logic (updating self.data) ...
        
        if self.master:
            self.persist_state()

    def get_data(self):
        if not self.master:
            try:
                # Slave simply relays the Master's state from the file
                with open(self.state_file, "r") as f:
                    return f.read(), 200, {'Content-Type': 'application/json'}
            except:
                return jsonify({"error": "Master not ready"}), 503
        
        # Master returns from its own live memory
        return jsonify(self.data)

    def toggle_config(self):
        data = request.get_json()
        for key, value in data.items():
            # 1. Update DB (Persistent Truth)
            cursor = self.db.cursor()
            cursor.execute("UPDATE ConfigTable SET Value = ? WHERE Key = ?", (int(value), key))
            self.db.commit()
            
            # 2. If this worker is master, update live memory immediately
            if self.master:
                setattr(self, f"config_{key}", value)
                self.log(action=f"Config {key} changed to {value}")

        return jsonify({"success": True})

    # ... keep the rest of your helper methods ...
"""
