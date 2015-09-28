"""web application for DOI landing pages"""

import sys
import flask
import doi

app = flask.Flask(__name__)

@app.errorhandler(404)
def not_found(error):
    return (flask.render_template('404.tmpl'), 404)

@app.errorhandler(406)
def not_found(error):
    return (flask.render_template('406.tmpl'), 406)

@app.route('/')
def index():
    dois = doi.get_all_dois()
    return flask.render_template('index.tmpl', 
                                 base_url=flask.request.script_root, dois=dois)

@app.route('/<path:identifier>')
def landing_page(identifier):
    try:
        d = doi.DOI('%s' % identifier)
    except doi.NotFoundError:
        flask.abort(404)
    mt = flask.request.accept_mimetypes.best_match(['text/html', 
                                                    'application/xml'])
    if mt is None:
        flask.abort(406)
    if mt == 'text/html':
        data = flask.render_template('landing_page.tmpl', doi=d)
    else:
        data = d.xml
    resp = flask.Response(data, mimetype=mt)
    return resp

if __name__ == '__main__':
    app.run(debug=True)

application = app
application.debug = True

# eof
