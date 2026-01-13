import requests
import os
from pprint import pprint
from security.keys import EXTERNAL_AUTH_TOKEN_API_V1, INTERNAL_AUTH_TOKEN
import json
from src.utils.constants import NETWORK_PATH
import sys
import random


def nuevo_pwd(url, correo):

    return requests.post(
        url=url + "/admin",
        params={
            "token": INTERNAL_AUTH_TOKEN,
            "solicitud": "nuevo_password",
            "correo": correo,
        },
    )


def get_pendientes(url):

    return requests.post(
        url=url + "/admin",
        params={
            "token": INTERNAL_AUTH_TOKEN,
            "solicitud": "get_pendientes",
        },
        json={},
    )


def get_faltan(url):

    return requests.post(
        url=url + "/admin",
        params={
            "token": INTERNAL_AUTH_TOKEN,
            "solicitud": "get_faltan",
        },
        json={},
    )


def manual_upload(url):

    target = os.path.join(NETWORK_PATH, "security", f"update_{int(args[2]):05d}.json")

    with open(target, "r") as f:
        payload = json.load(f)
        print(payload)

    return requests.post(
        url=url + "/admin",
        params={
            "token": INTERNAL_AUTH_TOKEN,
            "solicitud": "manual_upload",
        },
        json=payload,
    )


def force_update(url, id_member):

    return requests.post(
        url=url + "/admin",
        params={
            "token": INTERNAL_AUTH_TOKEN,
            "solicitud": "force_update",
        },
        json={"id_member": id_member},
    )


def alta_prueba(url, correo):

    clientes = [
        {
            "celular": "",
            "codigo_externo": f"MAQ-{str(random.randrange(9999))}",
            "correo": correo,
            "nombre": "Es una prueba",
            "numero_documento": "",
            "tipo_documento": "",
        },
    ]

    return requests.post(
        url=url + "/api/v1",
        headers=HEADER,
        json={
            "usuario": "USU-007",
            "solicitud": "alta",
            "clientes": clientes,
        },
    )


def baja_prueba(url, correo):

    clientes = [
        {
            "correo": correo,
        },
    ]

    return requests.post(
        url=url + "/api/v1",
        headers=HEADER,
        json={
            "usuario": "SEX-000",
            "solicitud": "baja",
            "clientes": clientes,
        },
    )


def mensajes_enviados_prueba(url):

    return requests.post(
        url=url + "/api/v1",
        headers=HEADER,
        json={
            "usuario": "SEX-000",
            "solicitud": "mensajes_enviados",
            "fecha_desde": "2025-12-01",
        },
    )


def clientes_autorizados(url):

    return requests.post(
        url=url + "/api/v1",
        headers=HEADER,
        json={
            "usuario": "SEX-000",
            "solicitud": "clientes_autorizados",
        },
    )


def kill_prueba(url, correo):

    return requests.post(
        url=url + "/admin",
        params={
            "token": INTERNAL_AUTH_TOKEN,
            "solicitud": "kill",
            "correo": correo,
        },
    )


url = "https://dev.nopasanadape.com"  # DEV
url = "http://localhost:5000"  # TEST
url = "https://nopasanadape.com"  # PROD
args = sys.argv

if len(args) < 2:
    print("Incompleto")
    quit()

HEADER = {
    "Authorization": "Bearer " + EXTERNAL_AUTH_TOKEN_API_V1,
    "Content-Type": "application/json",
}

if args[1] == "ALTA":
    f = alta_prueba(url, args[2])
    pprint(json.loads(f.content.decode()))

if args[1] == "KILL":
    f = kill_prueba(url, args[2])
    pprint(json.loads(f.content.decode()))

if args[1] == "MSG":
    f = mensajes_enviados_prueba(url)
    pprint(json.loads(f.content.decode()))

if args[1] == "BAJA":
    f = baja_prueba(url, args[2])
    pprint(json.loads(f.content.decode()))

if args[1] == "CLI":
    f = clientes_autorizados(url)
    pprint(json.loads(f.content.decode()))

if args[1] == "PEND":
    f = get_pendientes(url)
    pprint(json.loads(f.content.decode()))

if args[1] == "UPLOAD":
    f = manual_upload(url)
    pprint(json.loads(f.content.decode()))

if args[1] == "FALTAN":
    f = get_faltan(url)
    pprint(json.loads(f.content.decode()))

if args[1] == "FUERZA":
    f = force_update(url, args[2])
    pprint(json.loads(f.content.decode()))
