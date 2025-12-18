import os
import shutil
from datetime import datetime as dt
from src.utils.constants import NETWORK_PATH


def clear_outbound_folder(tipo=None):
    """
    borra todos los archivos de /outbound que cumplan con formato indicado
    default: todas las alertas y boletines
    """

    # en caso no se pasan parametros, usar default
    if not tipo:
        tipo = ("alerta", "boletin")

    # si solo tiene un string, convertir a lista
    if isinstance(tipo, str):
        tipo = [tipo]

    for file in os.listdir(os.path.join(NETWORK_PATH, "outbound")):
        for t in tipo:
            if t in file:
                os.remove(os.path.join(NETWORK_PATH, "outbound", file))


def post_maint(db_cursor):

    # review: duplicate placas
    cmd = """ DELETE FROM '$review';
                INSERT INTO '$review' 
                    SELECT NULL, Placa, "Placa Duplicada", NULL FROM placas GROUP BY Placa HAVING COUNT(*) > 1;
            """
    db_cursor.executescript(cmd)

    # review: placas with no associated member
    cmd = """ INSERT INTO '$review' SELECT NULL, Placa, "Placa sin Usuario", NULL FROM placas
                    WHERE IdMember_FK NOT IN (SELECT IdMember FROM members)
            """
    db_cursor.executescript(cmd)

    # manage the backups
    from_path = os.path.join(NETWORK_PATH, "data")
    target_path = os.path.join(NETWORK_PATH, "data", "backups")

    try:
        for filename in os.listdir(target_path):
            num = int(filename[2:4])
            if num == 8:
                os.remove(os.path.join(target_path, filename))
                continue
            new_filename = f"{filename[:2]}{num+1:02d}{filename[4:]}"
            os.rename(
                os.path.join(target_path, filename),
                os.path.join(target_path, new_filename),
            )

        _date = dt.strftime(dt.now(), "%Y-%m-%d %H;%M;%S")
        shutil.copy(
            os.path.join(from_path, "members.db"),
            os.path.join(target_path, f"m-00 [{_date}].db"),
        )
    except KeyboardInterrupt:  # Exception:
        print("***** Error BACKUP database ******")

    # TODO: eliminate all placas with IdMember_FK = 0 and LastUpdates old
    # TODO: extract text data from soat images
