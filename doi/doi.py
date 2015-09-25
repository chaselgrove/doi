"""DOIs"""

import json
import ezid
from .config import doi_prefix, auth0, auth1
from . import db

select_sql = "SELECT metadata, landing_page FROM doi WHERE identifier = %s"

insert_sql = """INSERT INTO doi (identifier, metadata, landing_page) 
                VALUES (%s, %s, %s)"""

update_metadata_sql = "UPDATE doi SET metadata = %s WHERE identifier = %s"

update_landing_page_sql = """UPDATE doi 
                                SET landing_page = %s 
                              WHERE identifier = %s"""

class DOI(ezid.DOI):

    def __init__(self, identifier):
        ezid.DOI.__init__(self, identifier)
        return

    def load(self):
        with db.DBCursor() as c:
            c.execute(select_sql, (self.identifier, ))
            if c.rowcount == 0:
                raise ezid.NotFoundError(self.identifier)
            row = c.fetchone()
            self.metadata = json.loads(row[0])
            self.landing_page = row[1]
        return

    def update_metadata(self, metadata):
        if self.identifier.startswith(doi_prefix):
            auth = auth0
        else:
            auth = auth1
        ezid.DOI.update_metadata(self, metadata, auth)
        with db.DBCursor() as c:
            c.execute(update_metadata_sql, 
                      (json.dumps(metadata), self.identifier))
        return

    def update_landing_page(self, landing_page):
        if self.identifier.startswith(doi_prefix):
            auth = auth0
        else:
            auth = auth1
        ezid.DOI.update_landing_page(self, landing_page, auth)
        with db.DBCursor() as c:
            c.execute(update_landing_page_sql, 
                      (self.landing_page, self.identifier))
        return

def mint(landing_page, metadata, test=False):
    if test:
        dp = ezid.test_prefix
        auth = auth0
    else:
        dp = doi_prefix
        auth = auth1
    identifier = ezid.mint(landing_page, metadata, dp, auth)
    with db.DBCursor() as c:
        params = (identifier, json.dumps(metadata), landing_page)
        c.execute(insert_sql, params)
    return identifier

def get_all_dois():
    with db.DBCursor() as c:
        c.execute("SELECT identifier FROM doi ORDER BY identifier")
        identifiers = [ row[0] for row in c ]
    dois = [ DOI(identifier) for identifier in identifiers ]
    return dois

# eof
