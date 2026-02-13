"""
Este archivo centraliza las reglas de tiempo para las alertas.
Define cuántos días antes o después de una fecha se debe disparar una acción.
"""

# Configuración de reglas
# 'dias_fijos': Lista de días exactos antes del vencimiento (ej. 5 días antes).
# 'rango_vencido': Tupla (inicio, fin) para alertas de "ya venció" (ej. de hoy hasta hace 3 días).

REGLAS = {
    "SOAT": {"dias_fijos": [10, 5], "rango_vencido": (0, -3)},
    "REVTEC": {"dias_fijos": [15, 7], "rango_vencido": (0, -3)},
    "BREVETE": {"dias_fijos": [30, 10], "rango_vencido": (0, -3)},
    "SATIMP": {"dias_fijos": [15, 5], "rango_vencido": (0, -3)},
}


def generar_sql_condicion(columna_fecha, tipo):
    """
    Genera un string SQL con las condiciones OR basadas en las reglas.

    Args:
        columna_fecha (str): El nombre de la columna SQL (ej. 'FechaHasta' o 's.FechaHasta').
        tipo (str): La clave del diccionario REGLAS (ej. 'SOAT').

    Returns:
        str: Fragmento SQL entre paréntesis.
    """
    regla = REGLAS.get(tipo)
    if not regla:
        # Si no existe la regla, retornamos 1=0 para que no traiga nada por seguridad
        return "(1=0)"

    condiciones = []

    # 1. Condiciones de días fijos (ej. Vence en 15 días)
    # DATE('now', '+15 days') = FechaHasta
    for dias in regla["dias_fijos"]:
        signo = "+" if dias >= 0 else ""
        sql = f"DATE('now', 'localtime', '{signo}{dias} days') = {columna_fecha}"
        condiciones.append(sql)

    # 2. Condición de rango vencido (ej. Venció hace 0 a 3 días)
    # DATE('now', '0 days') >= FechaHasta AND DATE('now', '-3 days') <= FechaHasta
    if regla.get("rango_vencido"):
        ini, fin = regla["rango_vencido"]
        sql_rango = (
            f"(DATE('now', 'localtime', '{ini} days') >= {columna_fecha} AND "
            f"DATE('now', 'localtime', '{fin} days') <= {columna_fecha})"
        )
        condiciones.append(sql_rango)

    # Unir todo con OR y encerrar en paréntesis
    return f"({' OR '.join(condiciones)})"
