import flask
import json

from flask import g
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager, current_user
from flask_sslify import SSLify

import settings

DB = SQLAlchemy()

import routes
from users.models import User


def create_app():
	app = flask.Flask(__name__)
	app.config.from_object(settings)

	DB.init_app(app)
	routes.configure_routes(app)

	app.jinja_env.filters['json'] = json.dumps
	SSLify(app)
	return app