from src.test.test_data import get_test_data_new
from src.updates import extrae_data_terceros
from src.server import do_updates
import sys


def main(db):

    i = sys.argv[1]

    # generar data de prueba
    data = [x for x in get_test_data_new(1) if i in x["Categoria"]][0]

    # iterar todas las pruebas
    print(f"[TEST] {data}")
    response = extrae_data_terceros.main(db, [data], headless=False)
    print("Prueba exitosa. Respuesta del scraper:")
    print(response)

    if response:
        do_updates.main(db, data=response)


if __name__ == "__main__":
    main()
