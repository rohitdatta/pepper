import requests
import settings
from functools import wraps
from flask import g, flash, redirect, url_for
from hashids import Hashids
import boto3
from itsdangerous import URLSafeTimedSerializer, URLSafeSerializer
import sendgrid
from sendgrid.helpers.mail import *

resume_hash = Hashids(min_length=8, salt=settings.HASHIDS_SALT)
s3 = boto3.resource('s3', aws_access_key_id=settings.AWS_ACCESS_KEY,
					aws_secret_access_key=settings.AWS_SECRET_KEY)
ts = URLSafeTimedSerializer(settings.SECRET_KEY)
s = URLSafeSerializer(settings.SECRET_KEY)
sg = sendgrid.SendGridAPIClient(apikey=settings.SENDGRID_API_KEY)


def validate_email(email):
	return requests.get(
		"https://api.mailgun.net/v3/address/validate",
		auth=("api", settings.MAILGUN_PUB_KEY),
		params={"address": email})

# A user who has any of these roles will be permitted to view this page
def roles_required(*role_names):
	def wrapper(func):
		@wraps(func)
		def decorated_view(*args, **kwargs):
			if not g.user.is_authenticated:
				return redirect(url_for('corp-login'))
			user_roles = [role.name for role in get_current_user_roles()]
			authorized = False
			for role in role_names:
				if role in user_roles:
					authorized = True
					break
			if not authorized:
				return 'Unauthorized'
			return func(*args, **kwargs)
		return decorated_view
	return wrapper


def get_current_user_roles():
	return g.user.roles

# Require user to be logged in and redirect unauthenticated users to corporate login screen
def corp_login_required(f):
	@wraps(f)
	def decorated_view(*args, **kwargs):
		if not g.user.is_authenticated:
			return redirect(url_for('corp-login'))
		return f(*args, **kwargs)
	return decorated_view

def send_email(from_email, subject, to_email, txt_content=None, html_content=None):
	recipient = Email(to_email)
	sender = Email(from_email)
	mail = Mail(sender, subject, recipient)
	if None in txt_content and html_content:
		raise ValueError('Must send some type of content')
	if txt_content:
		mail.add_content(Content('text/plain', txt_content))
	if html_content:
		mail.add_content(Content('text/html', html_content))
	response = sg.client.mail.send.post(request_body=mail.get())
	return response.status_code == 200