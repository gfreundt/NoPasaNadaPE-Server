import bcrypt, os
import sqlite3
import time

# local imports
NETWORK_PATH = os.path.join("/home", "gfreundt", "NoPasaNadaPE-Server")
DB_NETWORK_PATH = os.path.join(NETWORK_PATH, "data", "members.db")


def add_password():

    pwd_string = input("New Password: ")
    pwd_bytes = pwd_string.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)

    hash_bytes = bcrypt.hashpw(pwd_bytes, salt)
    hash_string = hash_bytes.decode("utf-8")

    print(hash_string)


def load_password():

    login_string = "perro21"
    login_bytes = login_string.encode("utf-8")

    pwd_bytes = login_string.strip().encode("utf-8")
    print(bcrypt.checkpw(login_bytes, pwd_bytes))


def hash_text(text_string):

    # plain text to bytes
    text_bytes = text_string.encode("utf-8")

    # generate random salt
    _salt = bcrypt.gensalt(rounds=12)

    # hash bytes using salt and return as plain text
    hash_bytes = bcrypt.hashpw(text_bytes, _salt)
    return hash_bytes.decode("utf-8")


def epwd():

    conn = sqlite3.connect(DB_NETWORK_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # cursor.execute(
    #     "UPDATE InfoMiembros SET Password = 'Kibri1' WHERE Correo = 'urpi@datum.com.pe'"
    # )
    # conn.commit()

    # quit()

    cursor.execute("SELECT Correo, Password FROM InfoMiembros")
    recs = cursor.fetchall()

    for rec in recs:
        newp = (
            rec["Password"] if "$2b$" in rec["Password"] else hash_text(rec["Password"])
        )
        print(rec["Correo"], rec["Password"], newp)
        cursor.execute(
            "UPDATE InfoMiembros SET Password = ? WHERE Correo = ?",
            (newp, rec["Correo"]),
        )

    conn.commit()

    # recs = cursor.execute("SELECT Correo, Password FROM InfoMiembros")

    # for r in recs:
    #     print(r["Password"])


epwd()
