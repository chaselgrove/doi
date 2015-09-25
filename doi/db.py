"""database routines"""

import psycopg2

dsn = "host=localhost dbname=doi user=doi password=doi"

class DBCursor:

    """context guard for database calls"""

    def __init__(self):
        return

    def __enter__(self):
        self.db = psycopg2.connect(dsn)
        self.c = self.db.cursor()
        return self.c

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.c.close()
        if exc_type:
            self.db.rollback()
        else:
            self.db.commit()
        self.db.close()
        return False

# eof
