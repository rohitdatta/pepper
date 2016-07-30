import requests
import settings
from functools import wraps
from flask import g, flash, redirect, url_for
from hashids import Hashids
import boto3

resume_hash = Hashids(min_length=8, salt=settings.HASHIDS_SALT)
s3 = boto3.resource('s3', aws_access_key_id=settings.AWS_ACCESS_KEY,
					aws_secret_access_key=settings.AWS_SECRET_KEY)

def validate_email(email):
	return requests.get(
		"https://api.mailgun.net/v3/address/validate",
		auth=("api", settings.MAILGUN_PUB_KEY),
		params={"address": email})


def roles_required(*role_names):
	def wrapper(func):
		@wraps(func)
		def decorated_view(*args, **kwargs):
			if not g.user.is_authenticated:
				return redirect(url_for('corp-login'))
			if not g.user.has_roles(*role_names):
				return 'Not authorized to view this page'
			return func(*args, **kwargs)
		return decorated_view
	return wrapper


def get_current_user_role():
	return g.user.roles

def corp_login_required(f):
	@wraps(f)
	def decorated_view(*args, **kwargs):
		if not g.user.is_authenticated:
			return redirect(url_for('corp-login'))
		return f(*args, **kwargs)
	return decorated_view