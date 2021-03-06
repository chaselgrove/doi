"""web application for DOI landing pages"""

import sys
import re
import flask
import requests
import doi

pubmed_re = re.compile('^\d+$')

form_dict_defaults = {'gender_female_checked': '', 
                      'gender_male_checked': '', 
                      'gender_either_checked': 'checked', 
                      'handedness_left_checked': '', 
                      'handedness_right_checked': '', 
                      'handedness_either_checked': 'checked', 
                      'age_min': '', 
                      'age_max': ''}

tag_dict_defaults = {'pubmed_id': '', 
                     'publication_doi': '', 
                     'authors': '', 
                     'funder': '', 
                     'description': '', 
                     'test': True}

def parse_search(form):
    """parse a search form

    returns a dictionary with the following keys:

        status: 200 or 400

        if 200:

            gender
            handedness
            age_range (tuple of two integers or None)

        if 400:

            error
            gender_female_checked
            gender_male_checked
            gender_either_checked
            handedness_left_checked
            handedness_right_checked
            handedness_either_checked
            age_min
            age_max
    """
    rd = {'gender_female_checked': '', 
          'gender_male_checked': '', 
          'gender_either_checked': '', 
          'handedness_left_checked': '', 
          'handedness_right_checked': '', 
          'handedness_either_checked': '', 
          'age_min': '', 
          'age_max': ''}
    error = None
    if form.has_key('age_min'):
        rd['age_min'] = form['age_min'].strip()
    else:
        rd['age_min'] = ''
    if form.has_key('age_max'):
        rd['age_max'] = form['age_max'].strip()
    else:
        rd['age_max'] = ''
    if form.has_key('gender'):
        rd['gender'] = form['gender']
        if form['gender'] == 'female':
            rd['gender_female_checked'] = 'checked'
        elif form['gender'] == 'male':
            rd['gender_male_checked'] = 'checked'
        elif form['gender'] == 'either':
            rd['gender_either_checked'] = 'checked'
        else:
            rd['gender_either_checked'] = 'checked'
            error = 'bad gender'
    else:
        rd['gender_either_checked'] = 'checked'
        error = 'no gender given'
    if form.has_key('handedness'):
        rd['handedness'] = form['handedness']
        if form['handedness'] == 'left':
            rd['handedness_left_checked'] = 'checked'
        elif form['handedness'] == 'right':
            rd['handedness_right_checked'] = 'checked'
        elif form['handedness'] == 'either':
            rd['handedness_either_checked'] = 'checked'
        else:
            rd['handedness_either_checked'] = 'checked'
            error = 'bad handedness'
    else:
        rd['handedness_either_checked'] = 'checked'
        error = 'no handedness given'
    if not rd['age_min']:
        age_min = None
    else:
        try:
            age_min = int(rd['age_min'])
        except:
            error = 'bad minimum age'
    if not rd['age_max']:
        age_max = None
    else:
        try:
            age_max = int(rd['age_max'])
        except:
            error = 'bad maximum age'
    if error:
        rd['status'] = 400
        rd['error'] = error
        return rd
    if age_min is None:
        if age_max is None:
            rd['age_range'] = None
        else:
            error = 'max age without min age'
    else:
        if age_max is None:
            error = 'min age without max age'
        else:
            if age_min > age_max:
                error = 'bad age range (min>max)'
            else:
                rd['age_range'] = (age_min, age_max)
    if error:
        rd['status'] = 400
        rd['error'] = error
        return rd
    rd['status'] = 200
    return rd

def parse_tag(form):
    """parse a tag form

    returns a dictionary with the following keys:

        status: 200 or 400

        if 200:

            pubmed_id
            publication_doi
            authors
            funder
            description
            test

        if 400, all 200 fields including:

            error
    """
    rd = dict(tag_dict_defaults)
    if form.has_key('pubmed_id'):
        rd['pubmed_id'] = form['pubmed_id'].strip()
    if form.has_key('publication_doi'):
        rd['publication_doi'] = form['publication_doi'].strip()
        if rd['publication_doi']:
            if not rd['publication_doi'].startswith('doi:'):
                rd['publication_doi'] = 'doi:' + rd['publication_doi']
    if form.has_key('authors'):
        rd['authors'] = []
        for author in form['authors'].split('\n'):
            author = author.strip()
            if not author:
                continue
            rd['authors'].append(author)
    if form.has_key('funder'):
        rd['funder'] = form['funder'].strip()
    if form.has_key('description'):
        rd['description'] = form['description']
    if form.has_key('not_test') and form['not_test'] == 'true':
        rd['test'] = False
    else:
        rd['test'] = True
    if not rd['description']:
        rd['error'] = 'no description given'
        rd['status'] = 400
        return rd
    if rd['pubmed_id']:
        if not pubmed_re.search(rd['pubmed_id']):
            rd['error'] = 'bad PubMed ID'
            rd['status'] = 400
            return rd
        url = 'http://www.ncbi.nlm.nih.gov/pubmed/%s' % rd['pubmed_id']
        r = requests.head(url)
        if r.status_code != 200:
            rd['error'] = 'PubMed ID not found'
            rd['status'] = 400
            return rd
    if rd['publication_doi']:
        url = 'http://dx.doi.org/%s' % rd['publication_doi']
        r = requests.head(url)
        if r.status_code not in (200, 303):
            rd['error'] = 'publication DOI not found'
            rd['status'] = 400
            return rd
    rd['status'] = 200
    return rd

app = flask.Flask(__name__)

@app.errorhandler(400)
def not_found(error):
    return (flask.render_template('400.tmpl', 
                                  script_root=flask.request.script_root), 400)

@app.errorhandler(404)
def not_found(error):
    return (flask.render_template('404.tmpl', 
                                  script_root=flask.request.script_root), 404)

@app.errorhandler(406)
def not_found(error):
    return (flask.render_template('406.tmpl', 
                                  script_root=flask.request.script_root), 406)

@app.route('/')
def index():
    return flask.render_template('search_index.tmpl', 
                                 script_root=flask.request.script_root, 
                                 post_url=flask.url_for('post_search'), 
                                 form_dict=form_dict_defaults, 
                                 error=None)

@app.route('/', methods=['POST'])
def post_search():
    res_dict = parse_search(flask.request.form)
    if res_dict['status'] == 400:
        return flask.render_template('search_index.tmpl', 
                                     script_root=flask.request.script_root, 
                                     post_url=flask.url_for('post_search'), 
                                     form_dict=res_dict, 
                                     error=res_dict['error'])
    search = doi.search(res_dict['gender'], 
                        res_dict['age_range'], 
                        res_dict['handedness'])
    return flask.redirect(flask.url_for('search', search_id=search.id))

@app.route('/<search_id>', methods=['GET', 'POST'])
def search(search_id):
    search_url = flask.url_for('search', search_id=search_id)
    tag_url = flask.url_for('tag', search_id=search_id)
    try:
        search = doi.get_search(search_id)
    except ValueError:
        flask.abort(404)
    projects = doi.get_all_projects()
    if flask.request.method == 'GET':
        return flask.render_template('search_search.tmpl', 
                                     script_root=flask.request.script_root, 
                                     search=search, 
                                     projects=projects, 
                                     post_url=search_url, 
                                     tag_url=tag_url, 
                                     error=None)
    excludes = []
    includes = []
    for name in flask.request.form.keys():
        if name.startswith('exclude_'):
            excludes.append(doi.get_image(name[8:]))
        if name.startswith('include_'):
            includes.append(doi.get_image(name[8:]))
    search.refine(excludes, includes, strict=False)
    return flask.render_template('search_search.tmpl', 
                                 script_root=flask.request.script_root, 
                                 search=search, 
                                 projects=projects, 
                                 post_url=search_url, 
                                 tag_url=tag_url, 
                                 error=None)

@app.route('/tag/<search_id>', methods=['GET', 'POST'])
def tag(search_id):
    search_url = flask.url_for('search', search_id=search_id)
    tag_url = flask.url_for('tag', search_id=search_id)
    try:
        search = doi.get_search(search_id)
    except ValueError:
        flask.abort(404)
    res_dict = tag_dict_defaults
    if flask.request.method == 'GET':
        return flask.render_template('search_tag.tmpl', 
                                     script_root=flask.request.script_root, 
                                     search=search, 
                                     post_url=tag_url, 
                                     search_url=search_url, 
                                     tag_form_dict=res_dict, 
                                     error=None)
    res_dict = parse_tag(flask.request.form)
    if res_dict['status'] == 200:
        if res_dict['pubmed_id']:
            pubmed_id = res_dict['pubmed_id']
        else:
            pubmed_id = None
        if res_dict['publication_doi']:
            publication_doi = res_dict['publication_doi']
        else:
            publication_doi = None
        if res_dict['authors']:
            authors = res_dict['authors']
        else:
            authors = None
        if res_dict['funder']:
            funder = res_dict['funder']
        else:
            funder = None
        if search.collection.identifier:
            # if this has been tagged with a test DOI but now needs to be made 
            # real
            if search.collection.doi.is_test and not res_dict['test']:
                search.collection.untag(update_others_flag=False)
        if search.collection.identifier:
            search.collection.add_info(res_dict['description'], 
                                       pubmed_id, 
                                       publication_doi, 
                                       authors, 
                                       funder)
        else:
            description = res_dict['description']
            search.collection.tag(description, 
                                  pubmed_id, 
                                  publication_doi, 
                                  authors, 
                                  funder, 
                                  update_others_flag=False, 
                                  test_flag=res_dict['test'])
        fmt = 'http://iaf.virtualbrain.org/lp/%s'
        url = fmt % search.collection.doi.identifier
        return flask.redirect(url)
    error = res_dict['error']
    return flask.render_template('search_tag.tmpl', 
                                 script_root=flask.request.script_root, 
                                 search=search, 
                                 post_url=tag_url, 
                                 search_url=search_url, 
                                 tag_form_dict=res_dict, 
                                 error=error)

@app.route('/reconstitute/<collection_id>')
def reconstitute(collection_id):
    try:
        collection = doi.get_collection(collection_id)
    except ValueError:
        flask.abort(404)
    s = doi.search_from_collection(collection)
    return flask.redirect(flask.url_for('search', search_id=s.id))

if __name__ == '__main__':
    app.run(debug=True)

application = app
application.debug = True

# eof
