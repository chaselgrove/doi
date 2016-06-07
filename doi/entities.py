"""DOI project entities"""

import hashlib
import random
import datetime
import re
from .doi import DOI, mint
from .db import DBCursor

bytes_re = re.compile('^(\d+) bytes$')
files_re = re.compile('^(\d+) files$')

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

_collection_info_sql = """SELECT * 
                            FROM collection_info 
                           WHERE collection = %s 
                           ORDER BY id"""

_insert_collection_info_sql = """INSERT INTO collection_info (collection, 
                                                              description, 
                                                              pubmed_id, 
                                                              pub_doi, 
                                                              funder) 
                                 VALUES (%s, %s, %s, %s, %s)"""

_collection_info_authors_sql = """SELECT author 
                                    FROM collection_info_author 
                                   WHERE collection_info = %s 
                                   ORDER BY id"""

_insert_collection_info_authors_sql = """INSERT INTO collection_info_author 
                                                     (collection_info, author) 
                                         VALUES (%s, %s)"""

_delete_collection_info_authors_sql = """DELETE FROM collection_info_author 
                                          WHERE collection_info IN 
                                                (SELECT id 
                                                 FROM collection_info 
                                                 WHERE collection = %s)"""

_delete_collection_info_sql = """DELETE FROM collection_info 
                                  WHERE collection = %s"""

_clear_collection_doi_sql = "UPDATE collection SET doi = NULL where id = %s"

class _Entity:

    def __init__(self, d):
        self.identifier = d['doi']
        self._doi = None
        return

    @property
    def doi(self):
        # self.identifier can be None for collections
        if self.identifier is None:
            return None
        if not self._doi:
            self._doi = DOI(self.identifier)
        return self._doi

    @property
    def title(self):
        return self.doi.metadata['title']

    @property
    def creators(self):
        return self.doi.metadata['creators']

    @property
    def publisher(self):
        return self.doi.metadata['publisher']

    @property
    def publicationyear(self):
        return self.doi.metadata['publicationyear']

    @property
    def resourcetype(self):
        return self.doi.metadata['resourcetype']

    @property
    def link(self):
        if 'alternateidentifiers' not in self.doi.metadata:
            return None
        for (type, identifier) in self.doi.metadata['alternateidentifiers']:
            if type == 'URL':
                return identifier
        return None

    @property
    def sizes(self):
        if 'sizes' not in self.doi.metadata:
            return []
        return self.doi.metadata['sizes']

    @property
    def relatedidentifiers(self):
        if 'relatedidentifiers' not in self.doi.metadata:
            return {}
        d = {}
        for t in self.doi.metadata['relatedidentifiers']:
            (identifier, type, relation) = t
            d.setdefault(relation, [])
            d[relation].append((type, identifier))
        return d

    @property
    def dates(self):
        if 'dates' not in self.doi.metadata:
            return {}
        d = {}
        for (type, date) in self.doi.metadata['dates']:
            d.setdefault(type, [])
            d[type].append(date)
        return d

    @property
    def version(self):
        if 'version' not in self.doi.metadata:
            return None
        return self.doi.metadata['version']

    @property
    def rights(self):
        if 'rights' not in self.doi.metadata:
            return []
        return self.doi.metadata['rights']

    @property
    def descriptions(self):
        if 'descriptions' not in self.doi.metadata:
            return []
        return self.doi.metadata['descriptions']

    @property
    def geolocations(self):
        if 'geolocations' not in self.doi.metadata:
            return []
        return self.doi.metadata['geolocations']

    @property
    def citation(self):
        """APA citation"""
        if len(self.creators) > 7:
            authors = ', '.join([ name for (name, _) in self.creators[:6] ])
            authors += ', ... %s' % self.creators[-1][0]
        else:
            authors = ', '.join([ name for (name, _) in self.creators[:-1] ])
            authors += ', & %s' % self.creators[-1][0]
        fmt = '%s. (%s).  %s.  %s.  http://dx.doi.org/%s.'
        citation = fmt % (authors, 
                          self.publicationyear, 
                          self.title, 
                          self.publisher, 
                          self.identifier)
        return citation

class _Project(_Entity):

    def __init__(self, d):
        _Entity.__init__(self, d)
        self.xnat_id = d['xnat_id']
        self._subjects = None
        return

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

    @property
    def contributors(self):
        if 'contributors' not in self.doi.metadata:
            return {}
        d = {}
        for (type, name, affiliation) in self.doi.metadata['contributors']:
            d.setdefault(type, [])
            d[type].append((name, affiliation))
        return d

    @property
    def formats(self):
        if 'formats' not in self.doi.metadata:
            return []
        return self.doi.metadata['formats']

    def note_collection(self, collection, update_flag=True):
        if not isinstance(collection, _Collection):
            raise TypeError('collection must be a _Collection instance')
        md = self.doi.copy_metadata()
        if 'relatedidentifiers' not in md:
            md['relatedidentifiers'] = []
        t = (collection.doi.identifier, 'DOI', 'IsSourceOf')
        md['relatedidentifiers'].append(t)
        self.doi.update_metadata(md, update_flag)
        return

    def unnote_collection(self, collection, update_flag=True):
        if not isinstance(collection, _Collection):
            raise TypeError('collection must be a _Collection instance')
        md = self.doi.copy_metadata()
        related_identifiers = md['relatedidentifiers']
        for ri in md['relatedidentifiers']:
            if ri[0] == collection.doi.identifier:
                md['relatedidentifiers'].remove(ri)
        self.doi.update_metadata(md, update_flag)
        return

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

class _Image(_Entity):

    def __init__(self, d):
        _Entity.__init__(self, d)
        self._project_xnat_id = d['project']
        self._project = None
        self._subject_label = d['subject']
        self._subject = None
        self._collections = None
        self.type = d['type']
        self.xnat_experiment_id = d['xnat_experiment_id']
        self.xnat_id = d['xnat_id']
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
    def format(self):
        if 'formats' not in self.doi.metadata:
            return []
        return self.doi.metadata['formats'][0]

    @property
    def collections(self):
        if self._collections is None:
            self._collections = []
            for (type, identifier) in self.relatedidentifiers['IsPartOf']:
                if identifier != self.project.identifier:
                    self._collections.append(get_collection_by_doi(identifier))
        return self._collections

    def note_collection(self, collection, update_flag=True):
        if not isinstance(collection, _Collection):
            raise TypeError('collection must be a _Collection instance')
        md = self.doi.copy_metadata()
        if 'relatedidentifiers' not in md:
            md['relatedidentifiers'] = []
        t = (collection.doi.identifier, 'DOI', 'IsPartOf')
        md['relatedidentifiers'].append(t)
        self.doi.update_metadata(md, update_flag)
        return

    def unnote_collection(self, collection, update_flag=True):
        if not isinstance(collection, _Collection):
            raise TypeError('collection must be a _Collection instance')
        md = self.doi.copy_metadata()
        for ri in md['relatedidentifiers']:
            if ri[0] == collection.doi.identifier:
                md['relatedidentifiers'].remove(ri)
        self.doi.update_metadata(md, update_flag)
        return

class _Collection(_Entity):

    def __init__(self, d):
        _Entity.__init__(self, d)
        # a DOI may not be assigned to a collection, so we have a unique ID 
        # and then a DOI which may or may not have a value
        self.id = d['id']
        self._images = None
        self._load_info()
        return

    def _load_info(self):
        self.info = []
        with DBCursor() as c:
            c.execute(_collection_info_sql, (self.id, ))
            cols = [ el[0] for el in c.description ]
            for row in c:
                self.info.append(dict(zip(cols, row)))
        with DBCursor() as c:
            for info in self.info:
                c.execute(_collection_info_authors_sql, (info['id'], ))
                info['authors'] = [ row[0] for row in c ]
        return

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

    def tag(self, 
            description, 
            pubmed_id=None, 
            publication_doi=None, 
            authors=None, 
            funder=None, 
            update_others_flag=True, 
            test_flag=False):
        """tag the collection with a DOI"""
        if self.identifier is not None:
            raise ValueError('collection has already been tagged')
        url = 'http://iaf.virtualbrain.org/search/reconstitute/%s' % self.id
        projects = {}
        for image in self.images:
            if image.project.identifier not in projects:
                projects[image.project.identifier] = image.project
        # get the creators from the source projects, staying unique over 
        # (name, affiliation)
        creator_dict = {}
        for project in projects.itervalues():
            for (name, affiliation) in project.creators:
                ident = '%s--%s' % (name, affiliation)
                creator_dict[ident] = (name, affiliation)
        creators = []
        for ident in sorted(creator_dict):
            creators.append(creator_dict[ident])
        md = {'creators': creators, 
              'title': '(:tba)', 
              'publisher': 'UMass/CANDI Image Attributation Framework', 
              'publicationyear': str(datetime.datetime.now().year), 
              'resourcetype': 'Dataset/Imaging Data', 
              'alternateidentifiers': [('URL', url)]}
        self._doi = mint(md, test_flag)
        self.identifier = self._doi.identifier
        md = self.doi.copy_metadata()
        md['title'] = 'Image collection %s' % self.doi.identifier
        md['relatedidentifiers'] = []
        for image in self.images:
            t = (image.identifier, 'DOI', 'HasPart')
            md['relatedidentifiers'].append(t)
            image.note_collection(self, update_others_flag)
        rights = set()
        for (identifier, project) in projects.iteritems():
            t = (identifier, 'DOI', 'IsDerivedFrom')
            md['relatedidentifiers'].append(t)
            project.note_collection(self, update_others_flag)
            rights.update(project.rights)
        md['rights'] = list(rights)
        with DBCursor() as c:
            c.execute("UPDATE collection SET doi = %s WHERE id = %s", 
                      (self.doi.identifier, self.id))
        formats = set()
        bytes = 0
        files = 0
        for image in self.images:
            for format in image.doi.metadata['formats']:
                formats.add(format)
            for size in image.doi.metadata['sizes']:
                mo = bytes_re.search(size)
                if mo:
                    bytes += int(mo.groups()[0])
                mo = files_re.search(size)
                if mo:
                    files += int(mo.groups()[0])
        md['formats'] = list(formats)
        md['sizes'] = ['%d bytes' % bytes, 
                       '%d files' % files, 
                       '%d images' % len(self.images)]
        self.doi.update_metadata(md)
        self.add_info(description, 
                      pubmed_id, 
                      publication_doi, 
                      authors, 
                      funder)
        return

    def untag(self, update_others_flag=True):
        """untag the collection (remove the DOI association)"""
        if self.identifier is None:
            raise ValueError('collection has not been tagged')
        with DBCursor() as c:
            c.execute(_delete_collection_info_authors_sql, (self.id, ))
            c.execute(_delete_collection_info_sql, (self.id, ))
            c.execute(_clear_collection_doi_sql, (self.id, ))
        projects = {}
        for image in self.images:
            if image.project.identifier not in projects:
                projects[image.project.identifier] = image.project
            image.unnote_collection(self, update_others_flag)
        for project in projects.itervalues():
            project.unnote_collection(self, update_others_flag)
        self.doi.remove_local()
        self._doi = None
        self.identifier = None
        return

    def add_info(self, 
                 description, 
                 pubmed_id=None, 
                 publication_doi=None, 
                 authors=None, 
                 funder=None):
        """update the collection DOI"""
        if self.identifier is None:
            raise ValueError('collection has not been tagged')
        with DBCursor() as c:
            params = (self.id, description, pubmed_id, publication_doi, funder)
            c.execute(_insert_collection_info_sql, params)
            c.execute("SELECT CURRVAL('collection_info_id_seq')")
            info_id = c.fetchone()[0]
            if authors:
                for author in authors:
                    params = (info_id, author)
                    c.execute(_insert_collection_info_authors_sql, params)
            self._load_info()
        md = self.doi.copy_metadata()
        if 'descriptions' not in md:
            md['descriptions'] = []
        md['descriptions'].append(('Other', description))
        if pubmed_id:
            if 'relatedidentifiers' not in md:
                md['relatedidentifiers'] = []
            ri = (pubmed_id, 'PMID', 'IsDocumentedBy')
            md['relatedidentifiers'].append(ri)
        if publication_doi:
            if 'relatedidentifiers' not in md:
                md['relatedidentifiers'] = []
            ri = (publication_doi, 'DOI', 'IsDocumentedBy')
            md['relatedidentifiers'].append(ri)
        if authors:
            if 'contributors' not in md:
                md['contributors'] = []
            for author in authors:
                md['contributors'].append(('RelatedPerson', author, None))
        if funder:
            if 'contributors' not in md:
                md['contributors'] = []
            md['contributors'].append(('Funder', funder, None))
        self.doi.update_metadata(md)
        return

    @property
    def formats(self):
        if 'formats' not in self.doi.metadata:
            return []
        return self.doi.metadata['formats']

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

    def set(self, collection):
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

    def modified(self):
        """report if the initial search has been modified"""
        return self._collection_id != self._initial_collection_id

    def refine(self, remove, add, strict=True):
        """refine the search results with lists of images

        unless strict is False, raises ValueError if any image in remove 
        is not in the collection or if any image in add is in the collection
        """
        if remove is None:
            remove = []
        if add is None:
            add = []
        for image in remove:
            if not isinstance(image, _Image):
                raise TypeError('non-image passed to update()')
        for image in add:
            if not isinstance(image, _Image):
                raise TypeError('non-image passed to update()')
        # add and remove based on identifiers (since the passed image objects 
        # may differ from the stored image objects)
        images = {}
        for image in self.collection.images:
            images[image.identifier] = image
        if strict:
            for image in add:
                if image.identifier in images:
                    fmt = 'image %s is already in search results'
                    raise ValueError(fmt % image.identifier)
            for image in remove:
                if image.identifier not in images:
                    fmt = 'image %s is not in search results'
                    raise ValueError(fmt % image.identifier)
            for image in remove:
                del images[image.identifier]
            for image in add:
                images[image.identifier] = image
        else:
            for image in remove:
                if image.identifier in images:
                    del images[image.identifier]
            for image in add:
                if image.identifier not in images:
                    images[image.identifier] = image
        collection = create_collection(images.values())
        self.set(collection)
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
        for row in c:
            d = dict(zip(cols, row))
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

def get_collection_by_doi(identifier):
    if not isinstance(identifier, basestring):
        raise TypeError('collection DOI must be a string')
    with DBCursor() as c:
        c.execute("SELECT * FROM collection WHERE doi = %s", (identifier, ))
        if c.rowcount == 0:
            raise ValueError('collection DOI %s not found' % identifier)
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
                continue
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

def search_from_collection(collection):
    if not isinstance(collection, _Collection):
        raise TypeError('collection must be a _Collection instance')
    search_id = random_identifier()
    if collection.doi:
        description = 'collection %s' % collection.doi.identifier
    else:
        description = 'pre-existing collection'
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

def get_all_collections():
    with DBCursor() as c:
        c.execute("SELECT * FROM collection")
        cols = [ el[0] for el in c.description ]
        row_dicts = [ dict(zip(cols, row)) for row in c ]
    return [ _Collection(rd) for rd in row_dicts ]

def get_entity(identifier):
    if not isinstance(identifier, basestring):
        raise TypeError('project identifier must be a string')
    with DBCursor() as c:
        c.execute("SELECT type FROM entity WHERE doi = %s", (identifier, ))
        if c.rowcount == 0:
            raise ValueError('identifier %s not found' % identifier)
        entity_type = c.fetchone()[0]
    if entity_type == 'project':
        return get_project(identifier)
    if entity_type == 'image':
        return get_image(identifier)
    if entity_type == 'collection':
        return get_collection_by_doi(identifier)
    raise ValueError('unknown entity type "%s"' % entity_type)

# eof
