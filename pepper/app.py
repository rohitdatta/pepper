import flask
import json

from flask import g, request, render_template
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager, current_user
from flask.ext.cdn import CDN
from flask_sslify import SSLify
from flask_redis import Redis
import sendgrid
import settings
import structlog
from rq import Queue
import redis

DB = SQLAlchemy()
redis_store = Redis()
sg = sendgrid.SendGridAPIClient(apikey=settings.SENDGRID_API_KEY)
cdn = CDN()
redis_url = settings.REDIS_URL
conn = redis.from_url(redis_url)
q = Queue(connection=conn)

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
	def processor(_, method, event):
		levelcolor = {
			'debug': 32,
			'info': 34,
			'warning': 33,
			'error': 31
		}.get(method, 37)

		return '\x1b[{clr}m{met}\x1b[0m [\x1b[35m{rid}\x1b[0m] {msg} {rest}'.format(
			clr=levelcolor,
			met=method.upper(),
			rid=request.headers.get('X-Request-Id', '~'),
			msg=event.pop('event'),
			rest=' '.join(['\x1b[%sm%s\x1b[0m=%s' % (levelcolor, k.upper(), v)
							for k, v in event.items()])
		)

	structlog.configure(
		processors=[
			structlog.processors.ExceptionPrettyPrinter(),
			processor
		]
	)

	logger = structlog.get_logger()

	@app.before_request
	def get_request_id():
		g.log = logger.new()

def setup_error_handlers(app):
	@app.errorhandler(404)
	def page_note_found(error):
		return render_template('layouts/error.html', title='Page Not Found', message="That page appear not to exist. Maybe you're looking for our <a href='{}' class='decorate'>homepage</a>?".format(settings.BASE_URL)), 404

	@app.errorhandler(500)
	def internal_error(error):
		g.log = g.log.bind(error=error)
		g.log.error('New 500 Error: ')
		return render_template('layouts/error.html', title='Internal Server Error', message='Something went wrong and we are unable to process this request. Our tech team has been alerted to this error and is working hard to fix it. We appreciate your patience! If this error continues, please email {}'.format(settings.GENERAL_INFO_EMAIL)), 500


def create_app():
	app = flask.Flask(__name__)
	app.config.from_object(settings)

	DB.init_app(app)
	redis_store.init_app(app)
	routes.configure_routes(app)
	configure_login(app)
	configure_logger(app)
	setup_error_handlers(app)

	app.jinja_env.filters['json'] = json.dumps

	app.config['CDN_DOMAIN'] = settings.CDN_URL
	app.config['CDN_HTTPS'] = True
	cdn.init_app(app)

	SSLify(app)
	return app
