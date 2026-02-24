import requests

url = "https://maq-apim.azure-api.net/wsMaqServicios/ProximoServicio"

headers = {
    "ApiMaq": "44c72d9b9a74418894d1a9ca5061a7f5",
    "Content-Type": "application/json",
}

payload = {"Placa": "CHO-571", "Documento": "40080207"}

try:
    response = requests.post(url, headers=headers, json=payload)

    print("Status code:", response.status_code)
    print("Response text:", response.text)

    # If response is JSON
    try:
        print("Response JSON:", response.json())
    except:
        pass

except requests.exceptions.RequestException as e:
    print("Request failed:", e)
