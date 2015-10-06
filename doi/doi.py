"""DOIs"""

import json
import ezid
from .config import umms_doi_prefix, umms_auth, test_auth
from . import db

base_lp_url = 'http://doi.virtualbrain.org'

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
        if self.identifier.startswith(umms_doi_prefix):
            auth = umms_auth
        else:
            auth = test_auth
        ezid.DOI.update_metadata(self, metadata, auth)
        with db.DBCursor() as c:
            c.execute(update_metadata_sql, 
                      (json.dumps(metadata), self.identifier))
        return

    def update_landing_page(self, landing_page):
        if self.identifier.startswith(umms_doi_prefix):
            auth = umms_auth
        else:
            auth = test_auth
        ezid.DOI.update_landing_page(self, landing_page, auth)
        with db.DBCursor() as c:
            c.execute(update_landing_page_sql, 
                      (self.landing_page, self.identifier))
        return

def mint(metadata, test=False):
    """mint a DOI using the test or UMMS prefix and set the landing page 
    to the virtualbrain landing page for the DOI

    returns the DOI object, not the identifier
    """
    if test:
        dp = ezid.test_prefix
        auth = test_auth
    else:
        dp = umms_doi_prefix
        auth = umms_auth
    identifier = ezid.mint(base_lp_url, metadata, dp, auth)
    md2 = ezid.validate_metadata(metadata)
    with db.DBCursor() as c:
        params = (identifier, json.dumps(md2), base_lp_url)
        c.execute(insert_sql, params)
    d = DOI(identifier)
    landing_page = '%s/lp/%s' % (base_lp_url, d.identifier)
    d.update_landing_page(landing_page)
    return d

def get_all_dois():
    with db.DBCursor() as c:
        c.execute("SELECT identifier FROM doi ORDER BY identifier")
        identifiers = [ row[0] for row in c ]
    dois = [ DOI(identifier) for identifier in identifiers ]
    return dois

# eof
