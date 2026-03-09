from src.server import database
from src.updates import extrae_data_terceros
from src.server import do_updates
from src.server import genera_data_pruebas
import sys


def main():

    db = database.Database()

    i = sys.argv[1]

    # generar data de prueba
    data = [
        x for x in genera_data_pruebas.generar(tamano_muestra=1) if i in x["Categoria"]
    ][0]

    # iterar todas las pruebas
    print(f"[TEST] {data}")
    response = extrae_data_terceros.main(db, [data], headless=False)
    print("Prueba exitosa. Respuesta del scraper:")
    if response:
        do_updates.main(db, data=response)
    for i in response:
        for j in i:
            print(j[:50])


if __name__ == "__main__":
    main()
