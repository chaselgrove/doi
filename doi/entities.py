"""DOI project entities"""

from .db import DBCursor

class Project:

    def __init__(self, doi):
        return

    def add_image(self, image):
        if not isinstance(image, Image):
            raise ValueError('image must be an Image instance')
        return

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

    def __init__(self, doi):
        return

class Collection:

    def __init__(self, doi):
        return

# eof
