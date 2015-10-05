"""web application for DOI landing pages"""

import sys
import flask
import doi

form_dict_defaults = {'gender_female_checked': '', 
                      'gender_male_checked': '', 
                      'gender_either_checked': 'checked', 
                      'handedness_left_checked': '', 
                      'handedness_right_checked': '', 
                      'handedness_either_checked': 'checked', 
                      'age_min': '', 
                      'age_max': ''}

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

app = flask.Flask(__name__)

@app.errorhandler(404)
def not_found(error):
    return (flask.render_template('404.tmpl'), 404)

@app.errorhandler(406)
def not_found(error):
    return (flask.render_template('406.tmpl'), 406)

@app.route('/')
def index():
    return flask.render_template('index.tmpl', 
                                 post_url=flask.url_for('post_search'), 
                                 form_dict=form_dict_defaults, 
                                 error=None)

@app.route('/', methods=['POST'])
def post_search():
    res_dict = parse_search(flask.request.form)
    if res_dict['status'] == 400:
        return flask.render_template('index.tmpl', 
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
    try:
        search = doi.get_search(search_id)
    except ValueError:
        flask.abort(404)
    projects = doi.get_all_projects()
    if flask.request.method == 'GET':
        return flask.render_template('search.tmpl', 
                                     search=search, 
                                     projects=projects, 
                                     post_url=search_url, 
                                     error=None)
    excludes = []
    includes = []
    for name in flask.request.form.keys():
        if name.startswith('exclude_'):
            excludes.append(doi.get_image(name[8:]))
        if name.startswith('include_'):
            includes.append(doi.get_image(name[8:]))
    search.refine(excludes, includes)
    return flask.render_template('search.tmpl', 
                                 search=search, 
                                 projects=projects, 
                                 post_url=search_url, 
                                 error=None)

if __name__ == '__main__':
    app.run(debug=True)

application = app
application.debug = True

# eof
