"""web application for DOI landing pages"""

import sys
import flask
import doi.entities

app = flask.Flask(__name__)

@app.template_filter('doi_link')
def doi_link(doi):
    return '<a href="http://dx.doi.org/%s">%s</a>' % (doi, doi)

@app.template_filter('pubmed_link')
def doi_link(pubmed_id):
    return '<a href="http://pubmed.org/%s">%s</a>' % (pubmed_id, pubmed_id)

@app.errorhandler(404)
def not_found(error):
    return (flask.render_template('lp_404.tmpl'), 404)

@app.errorhandler(406)
def not_acceptable(error):
    return (flask.render_template('lp_406.tmpl'), 406)

@app.errorhandler(500)
def internal_server_error(error):
    return (flask.render_template('lp_500.tmpl'), 500)

@app.route('/')
def index():
    return flask.redirect('http://doi.virtualbrain.org/')

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

    if mt == 'text/html':
        xml_url = flask.url_for('landing_page', 
                                identifier='xml/%s' % identifier)
        if isinstance(entity, doi.entities._Project):
            data = flask.render_template('lp_project.tmpl', 
                                         project=entity, 
                                         xml_url=xml_url)
        elif isinstance(entity, doi.entities._Image):
            data = flask.render_template('lp_image.tmpl', 
                                         image=entity, 
                                         xml_url=xml_url)
        elif isinstance(entity, doi.entities._Collection):
            data = flask.render_template('lp_collection.tmpl', 
                                         collection=entity, 
                                         xml_url=xml_url)
        else:
            flask.abort(500)
    else:
        data = entity.doi.xml
    resp = flask.Response(data, mimetype=mt)
    return resp

if __name__ == '__main__':
    app.run(debug=True)

application = app
application.debug = True

# eof
