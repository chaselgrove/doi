"""database routines"""

import psycopg2
from .config import db_host, db_database, db_user, db_password

_db = psycopg2.connect(host=db_host, 
                       dbname=db_database, 
                       user=db_user, 
                       password=db_password)

class DBCursor:

    """context guard for database calls"""

    def __init__(self):
        return

    def __enter__(self):
        self.c = _db.cursor()
        return self.c

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.c.close()
        if exc_type:
            _db.rollback()
        else:
            _db.commit()
        return False

# eof
