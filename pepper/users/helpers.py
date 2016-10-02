from pepper.utils import send_email
from pepper import settings
import random
from flask import render_template
from models import User
from sqlalchemy import or_
from pepper.app import DB
from flask import g
from flask.ext.rq import job
from pepper.app import rq

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


def handle_acceptances(modify_type, num_to_accept):
	print 'LOOOOGGGG'
	if modify_type == 'fifo':
		accepted_attendees = User.query.filter_by(status='PENDING').order_by(User.time_applied.asc()).limit(
			num_to_accept).all()
		for attendee in accepted_attendees:
			attendee.status = 'ACCEPTED'
			DB.session.commit()
			html = render_template('emails/application_decisions/accepted.html', user=attendee)
			# send_email(settings.GENERAL_INFO_EMAIL, "You're In! {} Invitation".format(settings.HACKATHON_NAME), attendee.email, html_content=html)
			g.log = g.log.bind(email=attendee.email)
			g.log.info('Sent email to')
	else:  # randomly select n users out of x users
		random_pool = User.query.filter(or_(User.status == 'PENDING', User.status == 'WAITLISTED')).all()
		accepted = random.sample(set(random_pool), num_to_accept)
		for attendee in accepted:
			if attendee.status == 'PENDING':
				html = render_template('emails/application_decisions/accepted.html', user=attendee)
			else:  # they got off waitlist
				html = render_template('emails/application_decisions/accept_from_waitlist.html', user=attendee)
			attendee.status = 'ACCEPTED'
			DB.session.commit()
			# send_email(settings.GENERAL_INFO_EMAIL, "You're In! {} Invitation".format(settings.HACKATHON_NAME),attendee.email, html_content=html)

		# set everyone else to go from pending to waitlisted
		pending_attendees = User.query.filter_by(status='PENDING').all()
		for pending_attendee in pending_attendees:
			pending_attendee.status = 'WAITLISTED'
			html = render_template('emails/application_decisions/waitlisted.html', user=pending_attendee)
			DB.session.commit()
			# send_email(settings.GENERAL_INFO_EMAIL, "You're {} Application Status".format(settings.HACKATHON_NAME), pending_attendee.email, html_content=html)