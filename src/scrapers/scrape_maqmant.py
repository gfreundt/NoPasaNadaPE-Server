import requests

from security.keys import API_MAQUINARIAS_TOKEN


def api(datos, timeout):

    placa = datos["Placa"]
    doc_num = datos["DocNum"]

    url = "https://maq-apim.azure-api.net/wsMaqServicios/ProximoServicio"

    headers = {
        "ApiMaq": API_MAQUINARIAS_TOKEN,
        "Content-Type": "application/json",
    }

    # si placa no tiene "-" al medio, incluirlo para que quede ABC-DEF
    if "-" not in placa:
        placa = f"{placa[:3]}-{placa[3:]}"

    # armar payload de consulta
    payload = {"Placa": placa, "Documento": doc_num}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)

        # respuesta correcta
        if response.status_code == 200:
            respuesta = response.json()

            # se encuentra el dato
            if respuesta["detalle"] == "OK":
                return [
                    (
                        respuesta["fecha_ultimo_servicio"],
                        respuesta["ultimo_servicio_detalle"],
                        respuesta["fecha_proximo_servicio"],
                        respuesta["proximo_servicio_detalle"],
                        datos["Placa"],
                    )
                ]

            # hay dato pero no coincide verificacion de placa-documento
            elif respuesta["detalle"] == "NRO IDENTIFICACIÓN NO ASIGNADO A LA PLACA":
                return []  # "Identificacion y Placa No Coinciden"

            # dato no tiene informacion
            else:
                return []

        else:
            return f"Error de Scraper: Status Code {response.status_code}"

    except requests.exceptions.RequestException as e:
        return f"Error de Scraper: {e[60]}"
