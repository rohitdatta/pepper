import json

import flask
from flask import g, request, render_template
from flask.ext.cdn import CDN
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager, current_user
from flask_redis import Redis
from flask_sslify import SSLify
from flask_wtf.csrf import CSRFProtect
import redis
from rq import Queue
import sendgrid
import settings
import structlog

DB = SQLAlchemy()
redis_store = Redis()
sg = sendgrid.SendGridAPIClient(apikey=settings.SENDGRID_API_KEY)
cdn = CDN()
conn = redis.from_url(settings.REDIS_URL)
worker_queue = Queue(connection=conn)
csrf = CSRFProtect()

import routes
from users.models import User


def configure_login(app):
	login_manager = LoginManager()
	login_manager.init_app(app)
	login_manager.login_view = 'login'
	login_manager.login_message = ''

	@login_manager.user_loader
	def load_user(id):
		return User.query.get(int(id))

	@app.before_request
	def before_request():
		g.user = current_user


def configure_logger(app):
	# Python's standard library logging was incomprehensible to me so
	# I'll write my own log level filtering processor
	log_levels = {
		'debug': 10,
		'info': 20,
		'warning': 30,
		'error': 40,
		'critical': 50,
	}
	app_log_level = log_levels.get(settings.LOG_LEVEL, 0)

	def filter_by_log_level(_, method, event):
		if log_levels.get(method, 0) < app_log_level:
			raise structlog.DropEvent
		return event

	def processor(_, method, event):
		# SGR parameters described here https://en.wikipedia.org/wiki/ANSI_escape_code
		levelcolor = {
			'debug': 32,
			'info': 34,
			'warning': 33,
			'error': 31,
			'critical': '31;1',
		}.get(method, 37)

		return '\x1b[{clr}m{met}\x1b[0m [\x1b[35m{rid}\x1b[0m] {msg} {rest}'.format(
			clr=levelcolor,
			met=method.upper(),
			rid=request.headers.get('X-Request-Id', '~'),
			msg=event.pop('event'),
			rest=' '.join('\x1b[{}m{}\x1b[0m={}'.format(levelcolor, k.upper(), v)
						  for k, v in event.items())
		)

	structlog.configure(
		processors=[
			filter_by_log_level,
			structlog.processors.UnicodeEncoder(),
			structlog.processors.ExceptionPrettyPrinter(),
			processor,
		],
	)

	logger = structlog.get_logger()

	@app.before_request
	def get_request_id():
		g.log = logger.new()
		if current_user.is_authenticated:
			g.log = g.log.bind(uid=current_user.id)


def setup_error_handlers(app):
	@app.errorhandler(404)
	def page_note_found(error):
		return render_template('layouts/error.html', title='Page Not Found',
							   message="That page appear not to exist. Maybe you're looking for our <a href='{}' class='decorate'>homepage</a>?".format(
								   settings.BASE_URL)), 404

	@app.errorhandler(500)
	def internal_error(error):
		g.log = g.log.bind(error=error)
		g.log.error('New 500 Error: ')
		return render_template('layouts/error.html', title='Internal Server Error',
							   message='Something went wrong and we are unable to process this request. Our tech team has been alerted to this error and is working hard to fix it. We appreciate your patience! If this error continues, please email {}'.format(
								   settings.GENERAL_INFO_EMAIL)), 500

	@app.errorhandler(400)
	def bad_request_error(error):
		g.log = g.log.bind(error=error)
		g.log.error('New 400 Error: ')
		return render_template('layouts/error.html', title='Bad Request',
							   message='We received invalid data and were unable to process this request. Please clear your cache and try again.'), 400


def setup_env_filters(app):
	app.jinja_env.filters['json'] = json.dumps

	def multisort(items, *attrs):
		return sorted(items, key=lambda x: tuple(getattr(x, attr) for attr in attrs))

	app.jinja_env.filters['multisort'] = multisort


def create_app():
	app = flask.Flask(__name__)
	app.config.from_object(settings)

	configure_logger(app)
	DB.init_app(app)
	csrf.init_app(app)
	redis_store.init_app(app)
	routes.configure_routes(app)
	configure_login(app)
	setup_error_handlers(app)
	setup_env_filters(app)

	app.config['CDN_DOMAIN'] = settings.CDN_URL
	app.config['CDN_HTTPS'] = True
	cdn.init_app(app)

	SSLify(app)
	return app
