from flask import Flask, render_template, jsonify, redirect, request
import threading
import logging
from copy import deepcopy as copy
import os
from datetime import datetime as dt, timedelta as td
import requests
import subprocess
import json
from collections import deque
import time
from src.dashboard import cron
from src.utils.utils import get_local_ip, vpn_online
from src.utils.constants import (
    NETWORK_PATH,
    TABLAS_BD,
)
from src.updates import gather_all
from src.server import do_updates
from src.dashboard import update_kpis
from src.utils.utils import start_vpn, stop_vpn, vpn_online
from src.updates import datos_actualizar, necesitan_mensajes
from src.comms import generar_mensajes, enviar_correo_mensajes
from pprint import pprint


logging.getLogger("werkzeug").disabled = True


class Dashboard:
    def __init__(self, db, soy_master):
        self.db = db
        self.data_lock = db.lock

        # crear estrcutura de variables y valores iniciales
        self.set_initial_data()

        # iniciar cron (procesos automaticos que corren cada cierto plazo) solo si es worker "master"
        if soy_master:
            cron.main(self)

    def set_server(self, server_instance):
        self.server = server_instance

    def set_initial_data(self):
        self.vpn_location = ""
        self.log_entries = deque(maxlen=55)
        self.assigned_cards = []
        self.config_autoscraper = False
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

    def log(self, **kwargs):

        print(kwargs)

        if "general_status" in kwargs:
            self.data["top_right"]["content"] = kwargs["general_status"][0]
            self.data["top_right"]["status"] = kwargs["general_status"][1]
            # write to permanent log in database

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
        """
        endpoint for dashboard to update continually on dashboard information:
        sends back a dictionary (self.data)
        """
        with self.data_lock:
            return jsonify(self.data)

    # -------- ACCIONES DE BOTONES ----------
    def datos_alerta(self):
        # solicitar actualizacion a servidor
        self.actualizar_datos = datos_actualizar.alertas(self.db)

        # actualizar kpis para dashboard con respuesta
        total = 0
        for key, val in zip(TABLAS_BD, self.actualizar_datos.values()):
            self.data["scrapers_kpis"][key]["alertas"] = len(val)
            total += len(val)
        self.data["scrapers_kpis"]["Acumulado"]["alertas"] = total

        return redirect("/dashboard")

    def datos_boletin(self):
        # solicitar actualizacion a servidor
        self.actualizar_datos = datos_actualizar.boletines(self.db)

        # actualizar kpis para dashboard con respuesta
        total = 0
        for key, val in zip(TABLAS_BD, self.actualizar_datos.values()):
            self.data["scrapers_kpis"][key]["boletines"] = len(val)
            total += len(val)
        self.data["scrapers_kpis"]["Acumulado"]["boletines"] = total

        # actualizar log de dashboard
        # self.log(action="[ DATOS BOLETIN ] Actualizado")
        return redirect("/dashboard")

    def actualizar(self):
        # logica general de scrapers
        scraper_responses = gather_all.gather_threads(
            dash=self, all_updates=self.actualizar_datos
        )

        # inserta resultado de scrapers en base de datos
        do_updates.main(db=self.db, data=scraper_responses)

        self.log(
            action=f"[ ACTUALIZACION ] Tamaño: {len(json.dumps(scraper_responses).encode("utf-8")) / 1024:.3f} kB",
        )
        return redirect("/dashboard")

    def generar_alertas(self):
        # genera todas las alertas que tocan y las guarda en "alertas_pendientes.json"
        mensajes = generar_mensajes.alertas(db=self.db)
        if len(mensajes) > 0:
            self.log(action=f"[ CREAR ALERTAS ] Total: {len(mensajes)}")

        # mantenerse en la misma pagina
        return redirect("/dashboard")

    def generar_boletines(self):
        # genera todos los boletines que tocan y los guarda en "boletines_pendientes.json"
        mensajes = generar_mensajes.boletines(db=self.db)
        if len(mensajes) > 0:
            self.log(action=f"[ CREAR BOLETINES ] Total: {len(mensajes)}")

        # mantenerse en la misma pagina
        return redirect("/dashboard")

    def enviar_mensajes(self):
        # envia todos los mensajes pendientes en "alertas_pendientes.json" y "boletines_pendientes.json"
        mensajes = enviar_correo_mensajes.send(db=self.db)
        if mensajes["ALERTA"] != 0 or mensajes["BOLETIN"] != 0:
            self.log(
                action=f"[ ENVIAR MENSAJES ] Alertas: {mensajes["ALERTA"]} | Boletines: {mensajes["BOLETIN"]}"
            )

        # mantenerse en la misma pagina
        return redirect("/dashboard")

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
            with self.data_lock:
                self.data["scrapers_en_linea"][service] = is_checked
            self.log(
                action=f"[ CONFIG ] Scraper {service} toggled {'ON' if is_checked else 'OFF'}"
            )
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Invalid service"}), 400

    def clear_logs(self):
        self.log_entries.clear()
        self.data["bottom_left"].clear()
        self.log(action="[ SISTEMA ] Registros de Log Limpiados.")
        return redirect("/")

    def db_vacuum(self):
        # mandar instruccion a Servidor
        _json = {"token": UPDATER_TOKEN, "instruction": "vacuum"}
        response = requests.post(url=self.url, json=_json)

        # actualizar log de dashboard
        if response.status_code == 200:
            self.log(action="[ MANTENIMIENTO ] Comando DB Vacuum enviado.")
        else:
            self.log(action=f"[ERROR] DB Vacuum: {response.status_code}")
        return redirect("/")

    def hacer_tests(self):
        try:
            tests.main(self)
        except KeyboardInterrupt:
            self.log(action="*** Cannot execute test (server offline?)")
        return redirect("/")

    def db_info(self):
        _json = {"token": UPDATER_TOKEN, "instruction": "get_info_data"}
        response = requests.post(url=self.url, json=_json).json()
        response.update({"Timestamp": str(dt.now())})
        with open(
            os.path.join(NETWORK_PATH, "security", "latest_info.json"), mode="w"
        ) as outfile:
            json.dump(response, outfile)
        self.log(action="DB Info Actualizada")
        return redirect("/")

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

                with self.data_lock:
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
        _json = {"token": UPDATER_TOKEN, "instruction": "get_logs", "max": 100}
        response = requests.post(url=self.url, json=_json)
        with open(
            os.path.join(NETWORK_PATH, "security", "latest_logs.json"), mode="w"
        ) as outfile:
            outfile.write(response.text)
            self.log(action="Logs Actualizados")
        return redirect("/")

    def db_completa(self):
        _json = {"token": UPDATER_TOKEN, "instruction": "get_entire_db"}
        response = requests.post(url=self.url, json=_json).json()
        response.update({"Timestamp": str(dt.now())})
        with open(
            os.path.join(
                NETWORK_PATH, "security", f"membersdb - {str(dt.now())[:10]}.json"
            ),
            mode="w",
        ) as outfile:
            json.dump(response, outfile)
        self.log(action=f"Copia Completa de BD: membersdb - {str(dt.now())[:10]}.json")
        return redirect("/")

    def actualizar_de_json(self):
        with open(
            os.path.join(NETWORK_PATH, "security", "last_update.json"), "r"
        ) as file:
            scraper_responses = json.load(file)
        self.log(
            action="Payload Size: "
            + str(len(json.dumps(scraper_responses).encode("utf-8")) / 1024 / 1024)
            + " MB",
        )
        _json = {
            "token": UPDATER_TOKEN,
            "instruction": "do_updates",
            "data": scraper_responses,
        }
        server_response = requests.post(url=self.url, json=_json)
        if server_response.status_code == 200:
            self.log(action="*** Actualizacion Completa")
        else:
            self.log(
                action=f"Error Enviando Actualizacion: {server_response.status_code}"
            )
        return redirect("/")

    def log_get(self):
        return jsonify(log="\n".join(self.log_entries))

    def run_in_background(self):
        flask_thread = threading.Thread(target=self.run, daemon=True)
        flask_thread.start()
        return flask_thread

    def runx(self):
        print("MONITOR RUNNING ON: http://localhost:7400/")
        self.app.run(debug=False, threaded=True, host="0.0.0.0", port=7400)
