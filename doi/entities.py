"""DOI project entities"""

from .doi import DOI
from .db import DBCursor

class Project:

    def __init__(self, identifier):
        with DBCursor() as c:
            c.execute("SELECT * FROM project WHERE doi = %s", (identifier, ))
            if c.rowcount == 0:
                raise ValueError('project %s not found')
            cols = [ el[0] for el in c.description ]
            d = dict(zip(cols, c.fetchone()))
            self.identifier = identifier
            self.xnat_id = d['xnat_id']
            self._doi = None
        return

    @property
    def doi(self):
        if self._doi:
            self._doi = DOI(self.identifier)
        return self._doi

class Subject:

    def __init__(self, id):
        with DBCursor() as c:
            c.execute("SELECT * FROM subject WHERE id = %s", (id, ))
            if c.rowcount == 0:
                raise ValueError('subject %s not found')
            cols = [ el[0] for el in c.description ]
            d = dict(zip(cols, c.fetchone()))
            self.id = id
            self.gender = d['gender']
            self.age = d['age']
            self.handedness = d['handedness']
            self._project_doi = d['project']
            self._project = None
        return

    @property
    def project(self):
        if not self._project:
            self._project = Project(self._project_doi)
        return self._project

class Image:

    def __init__(self, identifier):
        with DBCursor() as c:
            c.execute("SELECT * FROM image WHERE doi = %s", (identifier, ))
            if c.rowcount == 0:
                raise ValueError('image %s not found')
            cols = [ el[0] for el in c.description ]
            d = dict(zip(cols, c.fetchone()))
            self.identifier = identifier
            self._subject_id = d['subject']
            self._subject = None
            self.type = d['type']
            self.size = d['size']
            self._doi = None
        return

    @property
    def subject(self):
        if not self._subject:
            self._subject = Subject(self._subject_id)
        return self._subject

    @property
    def doi(self):
        if self._doi:
            self._doi = DOI(self.identifier)
        return self._doi

class Collection:

    def __init__(self, doi):
        with DBCursor() as c:
            c.execute("SELECT * FROM collection WHERE doi = %s", (identifier, ))
            if c.rowcount == 0:
                raise ValueError('collection %s not found')
            self.identifier = identifier
            self._doi = None
        return

    @property
    def doi(self):
        if self._doi:
            self._doi = DOI(self.identifier)
        return self._doi

# eof
