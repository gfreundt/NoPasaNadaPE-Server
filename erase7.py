e = {
    "IdPlaca_FK": None,
    "Aseguradora": 0,
    "Vigencia": 1,
    "FechaInicio": 2,
    "FechaHasta": 3,
    "PlacaValidate": 4,
    "Certificado": 5,
    "Uso": 6,
    "Clase": 7,
    "Tipo": 8,
    "FechaVenta": 9,
    "ImageBytes": None,
}


_r = [
    "Pacifico Seguros",
    "VIGENTE",
    "11/11/2025",
    "11/11/2026",
    "F2L100",
    "000000000201215119700100",
    "PARTICULAR",
    "CAMIONETA SUV/RURAL",
    "DIGITAL",
    "11/11/2025 12:04",
    "",
    "11/11/2026",
]

parte_payload = {key: _r[pos] if pos is not None else "" for key, pos in e.items()}
