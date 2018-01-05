from flask import Flask, render_template, make_response, request, g, abort
from logging.handlers import RotatingFileHandler
from werkzeug.exceptions import HTTPException
from flask_httpauth import HTTPBasicAuth
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache
import logging
import math
import os


# -----------------------------------------------------------
# Boot


app = Flask(__name__, static_url_path='')
app.config.from_pyfile('config.py')

app.config['LOGGER_HANDLER_POLICY'] = 'production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///storage/data/db.sqlite'
app.config['SQLALCHEMY_BINDS'] = {
    'servers_player_count': 'sqlite:///storage/data/servers_player_count.sqlite'
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['CACHE_TYPE'] = 'filesystem'
app.config['CACHE_DIR'] = 'storage/cache'
app.config['RANKS_IMAGES_DIR'] = 'static/images/ranks'
app.config['MINIMAPS_IMAGES_DIR'] = 'static/images/maps/minimap'
app.config['UNLOCKABLES_IMAGES_DIR'] = 'static/images/unlockables'
app.config['MY_USERNAME'] = 'epocdotfr'
app.config['CONTRIBUTORS'] = ['street veteran', 'mastock', 'dio']
app.config['DEVS'] = ['jackmayol', 'pasik', 'pasik2', 'tremozl', 'the soldier'] # ahnold
app.config['PLAYERS_LIST_PAGE_SIZES'] = [15, 30, 50, 100]

db = SQLAlchemy(app)
cache = Cache(app)
auth = HTTPBasicAuth()

handler = RotatingFileHandler('storage/logs/errors.log', maxBytes=10000000, backupCount=2)
handler.setLevel(logging.WARNING)
formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(message)s', datefmt='%d/%m/%Y %H:%M:%S')
handler.setFormatter(formatter)
app.logger.addHandler(handler)

from helpers import *
import rwr

app.jinja_env.filters.update(
    humanize_seconds=humanize_seconds,
    humanize_integer=humanize_integer
)

app.jinja_env.globals.update(
    int=int,
    float=float,
    str=str,
    round=round,
    abs=abs,
    fabs=math.fabs,
    isinstance=isinstance,
    PlayersSort=rwr.PlayersSort,
    merge_query_string_params=merge_query_string_params
)


# -----------------------------------------------------------
# After-init imports


import routes
import models
import commands


# -----------------------------------------------------------
# HTTP errors handler


@app.errorhandler(401)
@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(500)
@app.errorhandler(503)
def http_error_handler(error, without_code=False):
    if isinstance(error, HTTPException):
        error = error.code
    elif not isinstance(error, int):
        error = 500

    body = render_template('errors/{}.html'.format(error))

    if not without_code:
        return make_response(body, error)
    else:
        return make_response(body)


# -----------------------------------------------------------
# Hooks


@app.before_request
def define_globals():
    g.INCLUDE_WEB_ANALYTICS = not app.config['DEBUG']
    g.NO_INDEX = False
    g.UNDER_MAINTENANCE = False
    g.LAYOUT = 'normal'


@app.before_request
def check_under_maintenance():
    if request.endpoint != 'static' and os.path.exists('maintenance'):
        g.UNDER_MAINTENANCE = True

        abort(503)


@app.before_request
def get_counts():
    if request.endpoint != 'static':
        scraper = rwr.DataScraper()

        g.all_players_with_servers_details = scraper.get_all_players_with_servers_details()

        online_players, active_servers, total_servers = scraper.get_counters()

        g.online_players = online_players
        g.active_servers = active_servers
        g.total_servers = total_servers


@app.before_request
def set_beta_data():
    if request.endpoint != 'static' and app.config['BETA']:
        from git import Repo

        repo = Repo(app.root_path)

        g.BETA_BRANCH = repo.active_branch.name
        g.BETA_COMMIT = repo.head.commit.hexsha


@app.before_request
def check_beta_access():
    if request.endpoint != 'static' and app.config['BETA']:
        @auth.login_required
        def _check_login():
            return None

        return _check_login()


@app.url_defaults
def hashed_static_file(endpoint, values):
    """Add a cache-buster value in the URL of each static assets."""
    if endpoint == 'static':
        filename = values.get('filename')

        if filename:
            blueprint = request.blueprint

            if '.' in endpoint:
                blueprint = endpoint.rsplit('.', 1)[0]

            static_folder = app.static_folder

            if blueprint and app.blueprints[blueprint].static_folder:
                static_folder = app.blueprints[blueprint].static_folder

            fp = os.path.join(static_folder, filename)

            if os.path.exists(fp):
                values[int(os.stat(fp).st_mtime)] = ''


@auth.get_password
def get_password(username):
    if username in app.config['BETA_USERS']:
        return app.config['BETA_USERS'].get(username)

    return None


@auth.error_handler
def auth_error():
    return http_error_handler(403, without_code=True)
