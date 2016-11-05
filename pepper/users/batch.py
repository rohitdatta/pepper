from flask import render_template, render_template_string
from helpers import send_email
from pepper import settings

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

def accept_fifo():

def random_accept():
