#!/usr/bin/python

import xml.dom.minidom
import StringIO
import csv
import requests

def get_xnat_info(project, subject, experiment):
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

def process_files(parent_el):
    n_files = 0
    n_bytes = 0
    for el in parent_el.getElementsByTagName('xnat:file'):
        if el.getAttribute('label') == 'SNAPSHOTS':
            continue
        n_files += int(el.getAttribute('file_count'))
        n_bytes += int(el.getAttribute('file_size'))
    return (n_files, n_bytes)

def iteribsr():
    for i in xrange(18):
        subject = str(i+1)
        experiment = '%s_MR' % subject
        (scan_info, assessor_info) = get_xnat_info('ibsr', subject, experiment)
        d = {'Subject': subject, 
             'Type': 'Anatomical MR', 
             'Sizes': ('%d files' % scan_info[1], '%d bytes' % scan_info[2]), 
             'XNAT ID': scan_info[0]}
        yield d
        d = {'Subject': subject, 
             'Type': 'Manual Segmentation', 
             'Sizes': ('%d files' % assessor_info[1], 
                      '%d bytes' % assessor_info[2]), 
             'XNAT ID': assessor_info[0]}
        yield d
    return

def itercs():
    url = 'http://doi.virtualbrain.org/xnat/data/projects/cs_schizbull08/subjects?format=csv'
    r = requests.get(url)
    r = csv.reader(StringIO.StringIO(r.content))
    header = r.next()
    subjects = []
    for row in r:
        row_dict = dict(zip(header, row))
        subjects.append(row_dict['label'])
    for subject in subjects:
        experiment = '%s_MR' % subject
        (scan_info, assessor_info) = get_xnat_info('cs_schizbull08', subject, experiment)
        d = {'Subject': subject, 
             'Type': 'Anatomical MR', 
             'Sizes': ('%d files' % scan_info[1], '%d bytes' % scan_info[2]), 
             'XNAT ID': scan_info[0]}
        yield d
        d = {'Subject': subject, 
             'Type': 'Manual Segmentation', 
             'Sizes': ('%d files' % assessor_info[1], 
                      '%d bytes' % assessor_info[2]), 
             'XNAT ID': assessor_info[0]}
        yield d
    return

# eof
