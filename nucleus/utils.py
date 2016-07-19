import requests
import settings
from functools import wraps
from flask import g, flash, redirect, url_for

def validate_email(email):
	return requests.get(
		"https://api.mailgun.net/v3/address/validate",
		auth=("api", settings.MAILGUN_PUB_KEY),
		params={"address": email})


def required_roles(*roles):
	def wrapper(f):
		@wraps(f)
		def wrapped(*args, **kwargs):
			if get_current_user_role() not in roles:
				flash('Authentication error, please check your details and try again', 'error')
				return redirect(url_for('index'))
			return f(*args, **kwargs)

		return wrapped

	return wrapper


def get_current_user_role():
	return g.user.roles