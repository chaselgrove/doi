"""web application for DOI landing pages"""

import sys
import flask
import doi.entities

app = flask.Flask(__name__)

@app.errorhandler(404)
def not_found(error):
    return (flask.render_template('404.tmpl'), 404)

@app.errorhandler(406)
def not_acceptable(error):
    return (flask.render_template('406.tmpl'), 406)

@app.errorhandler(500)
def internal_server_error(error):
    return (flask.render_template('500.tmpl'), 500)

@app.route('/')
def index():
    dois = doi.get_all_dois()
    return flask.render_template('index.tmpl', 
                                 base_url=flask.request.script_root, dois=dois)

@app.route('/<path:identifier>')
def landing_page(identifier):
    if identifier.startswith('xml/'):
        identifier = identifier[4:]
        force_xml = True
    else:
        force_xml = False
    try:
        entity = doi.get_entity(identifier)
    except ValueError:
        flask.abort(404)
    if force_xml:
        mt = 'application/xml'
    else:
        mt = flask.request.accept_mimetypes.best_match(['text/html', 
                                                        'application/xml'])
        if mt is None:
            flask.abort(406)
    if isinstance(entity, doi.entities._Project):
        template = 'project.tmpl'
    elif isinstance(entity, doi.entities._Image):
        template = 'image.tmpl'
    elif isinstance(entity, doi.entities._Collection):
        template = 'collection.tmpl'
    else:
        flask.abort(500)
    if mt == 'text/html':
        xml_url = flask.url_for('landing_page', 
                                identifier='xml/%s' % identifier)
        data = flask.render_template(template, entity=entity, xml_url=xml_url)
    else:
        data = entity.doi.xml
    resp = flask.Response(data, mimetype=mt)
    return resp

if __name__ == '__main__':
    app.run(debug=True)

application = app
application.debug = True

# eof
