import psycopg2
from psycopg2 import OperationalError


def test_connection(host, user, password, database, port=5432):
    conn = None
    try:
        conn = psycopg2.connect(
            host=host,
            user=user,
            password=password,
            dbname=database,
            port=port
        )

        if conn.closed == 0:
            print(f"✅ Connesso con successo come '{user}'")

            # Test aggiuntivo: verifica le tabelle disponibili
            # cursor = conn.cursor()
            # cursor.execute("SHOW TABLES")
            # tables = cursor.fetchall()
            # print(f"📊 Tabelle nel database '{database}': {len(tables)}")
            # for table in tables:
            #    print(f"- {table[0]}")

    except OperationalError as e:
        print(f"❌ Errore durante la connessione come '{user}':")
        print(f"Messaggio completo: {e}")

        # Gestione specifica per errori PostgreSQL
        if "role" in str(e) and "does not exist" in str(e):
            print(">> Utente inesistente: verifica il nome utente")
        elif "password authentication failed" in str(e):
            print(">> Password errata")
        elif "could not connect" in str(e):
            print(">> Impossibile connettersi al server")
        elif "database does not exist" in str(e):
            print(f">> Database '{database}' non esistente")

    finally:
        if conn and conn.closed == 0:
            conn.close()


# Test con root
test_connection(
    host='127.0.0.1',
    user='postgres',
    password='',
    database='scacchi'
)

# Test con utente personalizzato
test_connection(
    host='127.0.0.1',
    user='utente_scacchi',
    password='password',
    database='scacchi'
)

# Extra: verifica con parametri errati (esempio didattico)
test_connection(
    host='127.0.0.1',
    user='utente_inesistente',
    password='wrong',
    database='scacchi'
)
