"""DOI project entities"""

import hashlib
import random
from .doi import DOI
from .db import DBCursor

_collection_images_sql = """SELECT * 
                              FROM image 
                             WHERE doi IN (SELECT image 
                                             FROM collection_image 
                                             WHERE collection = %s)"""

_insert_collection_image_sql = """INSERT INTO collection_image (collection, 
                                                                image) 
                                  VALUES (%s, %s)"""

_subject_images_sql = """SELECT * 
                           FROM image 
                          WHERE project = %s 
                            AND subject = %s 
                          ORDER BY type"""

_insert_search_sql = """INSERT INTO search (id, 
                                            description, 
                                            initial_collection, 
                                            collection) 
                        VALUES (%s, %s, %s, %s)"""

_update_search_sql = """UPDATE search 
                           SET t_modified = NOW(), 
                               collection = %s 
                         WHERE id = %s"""

_project_subjects_sql = """SELECT * 
                             FROM subject 
                            WHERE project = %s 
                            ORDER BY label"""

class _Project:

    def __init__(self, d):
        self.identifier = d['doi']
        self.xnat_id = d['xnat_id']
        self._doi = None
        self._subjects = None
        return

    @property
    def doi(self):
        if not self._doi:
            self._doi = DOI(self.identifier)
        return self._doi

    @property
    def subjects(self):
        if not self._subjects:
            self._subjects = []
            with DBCursor() as c:
                c.execute(_project_subjects_sql, (self.xnat_id, ))
                cols = [ el[0] for el in c.description ]
                for row in c:
                    row_dict = dict(zip(cols, row))
                    subject = _Subject(row_dict)
                    self._subjects.append(subject)
        return self._subjects

class _Subject:

    def __init__(self, d):
        self._project_xnat_id = d['project']
        self.label = d['label']
        self.xnat_id = d['xnat_id']
        self.gender = d['gender']
        self.age = d['age']
        self.handedness = d['handedness']
        self._project = None
        self._images = None
        return

    @property
    def project(self):
        if not self._project:
            self._project = get_project_by_xnat_id(self._project_xnat_id)
        return self._project

    @property
    def images(self):
        if self._images is None:
            self._images = []
            with DBCursor() as c:
                c.execute(_subject_images_sql, 
                          (self._project_xnat_id, self.label))
                cols = [ el[0] for el in c.description ]
                for row in c:
                    row_dict = dict(zip(cols, row))
                    image = _Image(row_dict)
                    self._images.append(image)
        return self._images

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
                c.execute(_collection_images_sql, (self.id, ))
                cols = [ el[0] for el in c.description ]
                for row in c:
                    row_dict = dict(zip(cols, row))
                    self._images.append(_Image(row_dict))
        return self._images

    def has_image(self, image):
        """preferred over 'image in self.images' in case different objects 
        refer to the same image"""
        for im in self.images:
            if image.doi.identifier == im.doi.identifier:
                return True
        return False

class _Search:

    def __init__(self, d):
        self.id = d['id']
        self.description = d['description']
        self.t_created = d['t_created']
        self._initial_collection_id = d['initial_collection']
        self._initial_collection = None
        self.t_modified = d['t_modified']
        self._collection_id = d['collection']
        self._collection = None
        return

    @property
    def initial_collection(self):
        if self._initial_collection is None:
            c = get_collection(self._initial_collection_id)
            self._initial_collection = c
        return self._initial_collection

    @property
    def collection(self):
        if self._collection is None:
            c = get_collection(self._collection_id)
            self._collection = c
        return self._collection

    def update(self, collection):
        if not isinstance(collection, _Collection):
            raise TypeError('collection is not a collection object')
        with DBCursor() as c:
            c.execute(_update_search_sql, (collection.id, self.id))
            c.execute("SELECT t_modified FROM search WHERE id = %s", 
                      (self.id, ))
            self._collection_id = collection.id
            self._collection = None
            self.t_modified = c.fetchone()[0]
        return

def create_identifier(s):
    if not isinstance(s, basestring):
        raise TypeError('argument must be a string')
    h = hashlib.sha256(s)
    return h.hexdigest()[:8]

def random_identifier():
    return create_identifier(str(random.random()))

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

def get_all_subjects():
    subjects = []
    with DBCursor() as c:
        c.execute("SELECT * FROM subject")
        cols = [ el[0] for el in c.description ]
        d = dict(zip(cols, c.fetchone()))
        subjects.append(_Subject(d))
    return subjects

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

def get_search(id):
    if not isinstance(id, basestring):
        raise TypeError('search ID must be a string')
    with DBCursor() as c:
        c.execute("SELECT * FROM search WHERE id = %s", (id, ))
        if c.rowcount == 0:
            raise ValueError('search %s not found' % id)
        cols = [ el[0] for el in c.description ]
        d = dict(zip(cols, c.fetchone()))
    return _Search(d)

def search(gender, age_range, handedness):
    if gender not in ('female', 'male', 'either'):
        raise ValueError('bad value for gender')
    if handedness not in ('left', 'right', 'either'):
        raise ValueError('bad value for handedness')
    if age_range is not None:
        if not isinstance(age_range, (tuple, list)):
            raise TypeError('age_range must be None, a tuple, or a list')
        if len(age_range) != 2:
            raise TypeError('age_range must be None or contain two values')
        for v in age_range:
            if not isinstance(v, int):
                msg = 'age_range must be None or contain two integers'
                raise TypeError(msg)
    images = []
    for subject in get_all_subjects():
        if gender == 'female' and subject.gender != 'female':
            continue
        if gender == 'male' and subject.gender != 'male':
            continue
        if handedness == 'left' and subject.handedness != 'left':
            continue
        if handedness == 'right' and subject.handedness != 'right':
            continue
        if age_range:
            if subject.age is None:
                conintue
            if subject.age < age_range[0] or subject.age > age_range[1]:
                continue
        images.extend(subject.images)
    description_parts = []
    if gender == 'either':
        description_parts.append('either gender')
    else:
        description_parts.append(gender)
    if not age_range:
        description_parts.append('any age')
    else:
        description_parts.append('%d <= age <= %d' % tuple(age_range))
    if handedness == 'either':
        description_parts.append('either handedness')
    else:
        description_parts.append(handedness)
    description = ', '.join(description_parts)
    collection = create_collection(images)
    search_id = random_identifier()
    with DBCursor() as c:
        params = (search_id, description, collection.id, collection.id)
        c.execute(_insert_search_sql, params)
    s = get_search(search_id)
    return s

def get_all_projects():
    projects = []
    with DBCursor() as c:
        c.execute("SELECT * FROM project ORDER BY xnat_id")
        cols = [ el[0] for el in c.description ]
        for row in c:
            row_dict = dict(zip(cols, row))
            project = _Project(row_dict)
            projects.append(project)
    return projects

# eof
