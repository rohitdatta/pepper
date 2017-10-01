from flask import render_template, render_template_string
from helpers import send_email
from pepper import settings
from models import User
from pepper.app import DB

from flask import g
from sqlalchemy import or_

import random

def send_batch_email(content, subject, users):
	lines = content.split('\r\n')
	msg_body = u""
	for line in lines:
		msg_body += u'<tr><td class="content-block">{}</td></tr>\n'.format(line)
	for user in users:
		html = render_template('emails/generic_message.html', content=msg_body)
		html = render_template_string(html, user=user)
		send_email(settings.GENERAL_INFO_EMAIL, subject, user.email, html_content=html)
		print 'Sent email'

def accept_fifo(num_to_accept, include_waitlist):
	if include_waitlist:
		potential_attendees = User.query.filter(or_(User.status == 'WAITLISTED', User.status == 'PENDING'))
	else:
		potential_attendees = User.query.filter_by(status='PENDING')
	ordered_attendees = potential_attendees.order_by(User.time_applied.asc()).limit(
			num_to_accept).all()

	for attendee in ordered_attendees:
		if attendee.status == 'WAITLISTED':
			html = render_template('emails/application_decisions/accept_from_waitlist.html', user=attendee)
		else: # User should be in pending state, but catch all just in case
			html = render_template('emails/application_decisions/accepted.html', user=attendee)
		attendee.status = 'ACCEPTED'
		DB.session.commit()
		send_email(settings.GENERAL_INFO_EMAIL, "Congrats! {} Invitation"
				   .format(settings.HACKATHON_NAME),
				   attendee.email, html_content=html)
		g.log = g.log.bind(email=attendee.email)
		g.log.info('Sent email to')


def random_accept(num_to_accept, include_waitlist):
	if include_waitlist:
		pool = User.query.filter(or_(User.status == 'PENDING', User.status == 'WAITLISTED')).all()
	else:
		pool = User.query.filter_by(status='PENDING').all()

	accepted = random.sample(set(pool), num_to_accept)
	for attendee in accepted:
		if attendee.status == 'PENDING':
			html = render_template('emails/application_decisions/accepted.html', user=attendee)
		else:  # they got off waitlist
			html = render_template('emails/application_decisions/accept_from_waitlist.html', user=attendee)
		attendee.status = 'ACCEPTED'
		DB.session.commit()
		send_email(settings.GENERAL_INFO_EMAIL, "You're In! {} Invitation".format(settings.HACKATHON_NAME), attendee.email, html_content=html)

	# set everyone else to go from pending to waitlisted
	pending_attendees = User.query.filter_by(status='PENDING').all()
	for pending_attendee in pending_attendees:
		pending_attendee.status = 'WAITLISTED'
		html = render_template('emails/application_decisions/waitlisted.html', user=pending_attendee)
		DB.session.commit()
		send_email(settings.GENERAL_INFO_EMAIL, "You're {} Application Status".format(settings.HACKATHON_NAME), pending_attendee.email, html_content=html)