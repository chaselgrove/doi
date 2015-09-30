"""DOI project entities"""

import hashlib
from .doi import DOI
from .db import DBCursor

_images_in_collection_sql = """SELECT * 
                                 FROM image 
                                WHERE doi IN (SELECT image 
                                                FROM collection_image 
                                                WHERE collection = %s)"""

_insert_collection_image_sql = """INSERT INTO collection_image (collection, 
                                                                image) 
                                  VALUES (%s, %s)"""

class _Project:

    def __init__(self, d):
        self.identifier = d['doi']
        self.xnat_id = d['xnat_id']
        self._doi = None
        return

    @property
    def doi(self):
        if not self._doi:
            self._doi = DOI(self.identifier)
        return self._doi

class _Subject:

    def __init__(self, d):
        self._project_xnat_id = d['project']
        self.label = d['label']
        self.xnat_id = d['xnat_id']
        self.gender = d['gender']
        self.age = d['age']
        self.handedness = d['handedness']
        self._project = None
        return

    @property
    def project(self):
        if not self._project:
            self._project = get_project_by_xnat_id(self._project_xnat_id)
        return self._project

class _Image:

    def __init__(self, d):
        self.identifier = d['doi']
        self._project_xnat_id = d['project']
        self._project = None
        self._subject_label = d['subject']
        self._subject = None
        self.type = d['type']
        self.xnat_id = d['xnat_id']
        self._doi = None
        return

    @property
    def subject(self):
        if not self._subject:
            self._subject = get_subject(self._project_xnat_id, 
                                        self._subject_label)
        return self._subject

    @property
    def project(self):
        if not self._project:
            self._project = get_project_by_xnat_id(self._project_xnat_id)
        return self._project

    @property
    def doi(self):
        if not self._doi:
            self._doi = DOI(self.identifier)
        return self._doi

class _Collection:

    def __init__(self, d):
        # a DOI may not be assigned to a collection, so we have a unique ID 
        # and then a DOI which may or may not have a value
        self.id = d['id']
        self._doi = d['doi']
        self._images = None
        return

    @property
    def doi(self):
        # return None if no DOI is assigned; the resolve the DOI to a DOI 
        # object if we need to
        if self._doi is None:
            return self._doi
        if isinstance(self._doi, basestring):
            self._doi = doi.DOI(self._doi)
        return self._doi

    @property
    def images(self):
        if self._images is None:
            self._images = []
            with DBCursor() as c:
                c.execute(_images_in_collection_sql, (self.id, ))
                cols = [ el[0] for el in c.description ]
                for row in c:
                    row_dict = dict(zip(cols, row))
                    self._images.append(_Image(row_dict))
        return self._images

def create_identifier(s):
    if not isinstance(s, basestring):
        raise TypeError('argument must be a string')
    h = hashlib.sha256(s)
    return h.hexdigest()[:8]

def get_project(identifier):
    if not isinstance(identifier, basestring):
        raise TypeError('project identifier must be a string')
    with DBCursor() as c:
        c.execute("SELECT * FROM project WHERE doi = %s", (identifier, ))
        if c.rowcount == 0:
            raise ValueError('project %s not found' % identifier)
        cols = [ el[0] for el in c.description ]
        d = dict(zip(cols, c.fetchone()))
    return _Project(d)

def get_project_by_xnat_id(xnat_id):
    if not isinstance(xnat_id, basestring):
        raise TypeError('project XNAT ID must be a string')
    with DBCursor() as c:
        c.execute("SELECT * FROM project WHERE xnat_id = %s", (xnat_id, ))
        if c.rowcount == 0:
            raise ValueError('project %s not found' % identifier)
        cols = [ el[0] for el in c.description ]
        d = dict(zip(cols, c.fetchone()))
    return _Project(d)

def get_subject(project, label):
    if not isinstance(project, basestring):
        raise TypeError('subject project must be a string')
    if not isinstance(label, basestring):
        raise TypeError('subject label must be a string')
    with DBCursor() as c:
        c.execute("SELECT * FROM subject WHERE project = %s AND label = %s", 
                  (project, label))
        if c.rowcount == 0:
            raise ValueError('subject %s not found' % id)
        cols = [ el[0] for el in c.description ]
        d = dict(zip(cols, c.fetchone()))
    return _Subject(d)

def get_image(identifier):
    if not isinstance(identifier, basestring):
        raise TypeError('image identifier must be a string')
    with DBCursor() as c:
        c.execute("SELECT * FROM image WHERE doi = %s", (identifier, ))
        if c.rowcount == 0:
            raise ValueError('image %s not found' % identifier)
        cols = [ el[0] for el in c.description ]
        d = dict(zip(cols, c.fetchone()))
    return _Image(d)

def get_collection(id):
    if not isinstance(id, basestring):
        raise TypeError('collection ID must be a string')
    with DBCursor() as c:
        c.execute("SELECT * FROM collection WHERE id = %s", (id, ))
        if c.rowcount == 0:
            raise ValueError('collection %s not found' % id)
        cols = [ el[0] for el in c.description ]
        d = dict(zip(cols, c.fetchone()))
    return _Collection(d)

def create_collection(images):
    if not isinstance(images, (tuple, list)):
        raise TypeError('images must be a tuple or list')
    for im in images:
        if not isinstance(im, _Image):
            raise TypeError('images must be image objects')
    image_ids = [ image.identifier for image in images ]
    image_ids.sort()
    id_string = ':'.join(image_ids)
    identifier = create_identifier(id_string)
    try:
        collection = get_collection(identifier)
    except ValueError:
        pass
    else:
        return collection
    with DBCursor() as c:
        c.execute("INSERT INTO collection (id, doi) VALUES (%s, NULL)", 
                  (identifier, ))
        for image_id in image_ids:
            c.execute(_insert_collection_image_sql, (identifier, image_id))
    collection = get_collection(identifier)
    return collection

# eof
