#!/usr/bin/python

import xml.dom.minidom
import StringIO
import csv
import requests
from ezid.xml_utils import xml_text

# restrict created data to certain subjects (project code, subject label)
# subject_subset = None for all subjects
subjects_subset = (('cs_schizbull08', 'BPDwPsy_066'), 
                   ('cs_schizbull08', 'HC_001'), 
                   ('ibsr', '14'), 
                   ('ibsr', '8'))
subjects_subset = None

subjects = {}

def get_subjects(project):
    if project not in subjects:
        url = 'http://doi.virtualbrain.org/xnat/data/projects/%s/subjects?format=csv' % project
        r = requests.get(url)
        r = csv.reader(StringIO.StringIO(r.content))
        header = r.next()
        subjects[project] = []
        for row in r:
            row_dict = dict(zip(header, row))
            if subjects_subset:
                if (project, row_dict['label']) not in subjects_subset:
                    continue
            subjects[project].append(row_dict['label'])
    return subjects[project]

def get_image_info(project, subject, experiment):
    """for the given project, subject, and experiment, returns a 2-tuple of:

        (experiment ID, N scan files, N scan file bytes), 
        (assessor ID, N assessor files, N assessor file bytes)
    """
    url = 'http://doi.virtualbrain.org/xnat/data/projects/'
    url += project
    url += '/subjects/'
    url += subject
    url += '/experiments/'
    url += experiment
    url += '?format=xml'
    r = requests.get(url)
    doc = xml.dom.minidom.parseString(r.content)
    els = doc.getElementsByTagName('xnat:MRSession')
    experiment_id = els[0].getAttribute('ID')
    els = doc.getElementsByTagName('xnat:assessor')
    assert len(els) == 1
    assessor_el = els[0]
    assessor_id = assessor_el.getAttribute('ID')
    els = doc.getElementsByTagName('xnat:scans')
    assert len(els) == 1
    scan_el = els[0]
    (n_scan_files, n_scan_bytes) = process_files(scan_el)
    (n_assessor_files, n_assessor_bytes) = process_files(assessor_el)
    return ((experiment_id, n_scan_files, n_scan_bytes), 
            (assessor_id, n_assessor_files, n_assessor_bytes))

def get_subject_info(project, subject):
    """return (XNAT ID, gender, age, handedness) for an XNAT subject"""
    url = 'http://doi.virtualbrain.org/xnat/data/projects/'
    url += project
    url += '/subjects/'
    url += subject
    url += '?format=xml'
    r = requests.get(url)
    doc = xml.dom.minidom.parseString(r.content)
    els = doc.getElementsByTagName('xnat:Subject')
    xnat_id = els[0].getAttribute('ID')
    age_els = doc.getElementsByTagName('xnat:age')
    if age_els:
        age = xml_text(age_els[0])
    else:
        age = None
    gender_els = doc.getElementsByTagName('xnat:gender')
    gender = xml_text(gender_els[0])
    handedness_els = doc.getElementsByTagName('xnat:handedness')
    if handedness_els:
        handedness = xml_text(handedness_els[0])
    else:
        handedness = None
    return (xnat_id, gender, age, handedness)

def process_files(parent_el):
    n_files = 0
    n_bytes = 0
    for el in parent_el.getElementsByTagName('xnat:file'):
        if el.getAttribute('label') == 'SNAPSHOTS':
            continue
        n_files += int(el.getAttribute('file_count'))
        n_bytes += int(el.getAttribute('file_size'))
    return (n_files, n_bytes)

def iter_subjects(project):
    for subject in get_subjects(project):
        (xnat_id, gender, age, handedness) = get_subject_info(project, subject)
        if gender in ('F', 'female'):
            gender_norm = 'female'
        elif gender in ('M', 'male'):
            gender_norm = 'male'
        else:
            msg = 'gender %s for subject %s in %s' % (gender, subject, project)
            raise ValueError(msg)
        d = {'XNAT ID': xnat_id, 
             'label': subject, 
             'gender': gender_norm, 
             'age': age, 
             'handedness': handedness}
        yield d
    return

def iter_images(project):
    if project == 'cs_schizbull08':
        format = 'NIfTI-1'
    elif project == 'ibsr':
        format = 'ANALYZE'
    else:
        raise ValueError('bad project')
    for subject in get_subjects(project):
        experiment = '%s_MR' % subject
        (scan_info, assessor_info) = get_image_info(project, 
                                                    subject, 
                                                    experiment)
        experiment_id = scan_info[0]
        d = {'subject': subject, 
             'type': 'Anatomical MR', 
             'format': format, 
             'sizes': ('%d files' % scan_info[1], 
                       '%d bytes' % scan_info[2]), 
             'XNAT experiment ID': experiment_id, 
             'XNAT ID': experiment_id}
        yield d
        d = {'subject': subject, 
             'type': 'Manual Segmentation', 
             'format': format, 
             'sizes': ('%d files' % assessor_info[1], 
                      '%d bytes' % assessor_info[2]), 
             'XNAT experiment ID': experiment_id, 
             'XNAT ID': assessor_info[0]}
        yield d
    return

# eof
