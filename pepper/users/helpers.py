from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from pepper.utils import send_email, s
from pepper import settings
from flask import render_template, url_for, flash

def hash_pwd(password):
	return generate_password_hash(password)

def check_password(hashed, password):
	return check_password_hash(hashed, password)

def send_status_change_notification(user):
	if user.status == 'ACCEPTED':
		# txt = render_template('')
		subject = "Congratulations! You've been accepted to {}".format(settings.HACKATHON_NAME)
	elif user.status == 'REJECTED':
		# txt =
		subject = "Your {} application decision".format(settings.HACKATHON_NAME)
	elif user.status == 'WAITLISTED':
		# txt =
		subject = "Update on your application to {}".format(settings.HACKATHON_NAME)

	# send_email('hello@hacktx.com', subject, user.email, txt, html)

def send_recruiter_invite(user):
	# send invite to the recruiter
	token = s.dumps(user.email)
	url = url_for('new-user-setup', token=token, _external=True)
	txt = render_template('emails/corporate_welcome.txt', user=user, setup_url=url)
	html = render_template('emails/corporate_welcome.html', user=user, setup_url=url)

	try:
		send_email(from_email=settings.GENERAL_INFO_EMAIL,
						  subject='Your invitation to join my{}'.format(settings.HACKATHON_NAME),
						  to_email=user.email, txt_content=txt, html_content=html)
	except Exception as e:
		g.log = g.log.bind(error=e)
		g.log.error('Unable to send recruiter email: ')