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
    base_url = 'http://www.ncbi.nlm.nih.gov/pubmed/'
    return '<a href="%s?term=%s">PMID %s</a>' % (base_url, pubmed_id, pubmed_id)

@app.template_filter('render_contributor')
def render_contributor(contact):
    (name, affiliation) = contact
    if affiliation:
        return '%s (%s)' % (name, affiliation)
    return name

@app.errorhandler(404)
def not_found(error):
    return (flask.render_template('404.tmpl', 
                                  script_root=flask.request.script_root), 404)

@app.errorhandler(406)
def not_acceptable(error):
    return (flask.render_template('406.tmpl', 
                                  script_root=flask.request.script_root), 406)

@app.errorhandler(500)
def internal_server_error(error):
    return (flask.render_template('500.tmpl', 
                                  script_root=flask.request.script_root), 500)

@app.route('/')
def index():
    return flask.redirect('http://iaf.virtualbrain.org/')

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
                                         script_root=flask.request.script_root, 
                                         project=entity, 
                                         xml_url=xml_url)
        elif isinstance(entity, doi.entities._Image):
            data = flask.render_template('lp_image.tmpl', 
                                         script_root=flask.request.script_root, 
                                         image=entity, 
                                         xml_url=xml_url)
        elif isinstance(entity, doi.entities._Collection):
            data = flask.render_template('lp_collection.tmpl', 
                                         script_root=flask.request.script_root, 
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
