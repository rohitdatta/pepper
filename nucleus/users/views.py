from flask.ext.login import login_user, logout_user, current_user, login_required
from flask import request, render_template, redirect, url_for, flash
import requests
from models import User
from nucleus.app import DB
from sqlalchemy.exc import IntegrityError
from nucleus import settings
import sendgrid
from sendgrid.helpers.mail import *
import urllib2

def landing():
	if current_user.is_authenticated:
		return redirect(url_for('dashboard'))
	return render_template("static_pages/index.html")

def dashboard():
	if current_user.status == 'ACCEPTED':
		return redirect(url_for('accept-invite'))
	elif current_user.status == 'CONFIRMED':
		return render_template('users/confirmed.html')
	return render_template('users/dashboard.html', user=current_user)

def login():
	return redirect('https://my.mlh.io/oauth/authorize?client_id={0}&redirect_uri={1}%2Fcallback&response_type=code'.format(settings.MLH_APPLICATION_ID, urllib2.quote(settings.BASE_URL)))

def callback():
	url = 'https://my.mlh.io/oauth/token?client_id={0}&client_secret={1}&code={2}&redirect_uri={3}callback&grant_type=authorization_code'.format(settings.MLH_APPLICATION_ID, settings.MLH_SECRET, request.args.get('code'), urllib2.quote(settings.BASE_URL, ''))
	print url
	resp = requests.post(url)
	# print resp.headers
	access_token = resp.json()['access_token']
	print 'ACCESS TOKEN:' + access_token
	user = User.query.filter_by(email=access_token).first()
	if user is None: # create the user
		try:
			user_info = requests.get('https://my.mlh.io/api/v1/user?access_token={0}'.format(access_token)).json()
			user = User(user_info)
			DB.session.add(user)
			DB.session.commit()
			login_user(user, remember=True)
		except IntegrityError:
			# a unique value already exists this should never happen
			DB.session.rollback()
			flash('A fatal error occurred. Please contact us for help', 'error')
			return render_template('static_pages/index.html')
	else:
		login_user(user, remember=True)
		return redirect(url_for('dashboard'))
	return redirect(url_for('confirm-registration'))

@login_required
def confirm_registration():
	if request.method == 'GET':
		return render_template('users/confirm.html', user=current_user)
	else:
		current_user.status = 'PENDING'
		DB.session.add(current_user)
		DB.session.commit()
		# send a confirmation email. TODO: this is kinda verbose and long
		sg = sendgrid.SendGridAPIClient(apikey=settings.SENDGRID_API_KEY)
		from_email = Email(settings.GENERAL_INFO_EMAIL)
		subject = 'Thank you for applying to {0}'.format(settings.HACKATHON_NAME)
		to_email = Email(current_user.email)
		content = Content('text/plain', 'Thanks for applying to {0}'.format(settings.HACKATHON_NAME))
		mail = Mail(from_email, subject, to_email, content)
		response = sg.client.mail.send.post(request_body=mail.get())
		print response.status_code
		flash('Congratulations! You have successfully applied for {0}! You should receive a confirmation email shortly'.format(settings.HACKATHON_NAME), 'success')
		return redirect(url_for('dashboard'))

@login_required
def logout():
	logout_user()
	return redirect(url_for('landing'))

@login_required
def accept():
	if current_user.status != 'ACCEPTED':  # they aren't allowed to accept their invitation
		message = {
			'PENDING': "You haven't been accepted to {0}! Please wait for your invitation before visiting this page!".format(
				settings.HACKATHON_NAME),
			'CONFIRMED': "You've already accepted your invitation to {0}! We look forward to seeing you here!".format(
				settings.HACKATHON_NAME),
			'REJECTED': "You've already rejected your {0} invitation. Unfortunately, for space considerations you cannot change your response.".format(
				settings.HACKATHON_NAME)
		}
		flash(message[current_user.status], 'error')
		return redirect(url_for('dashboard'))
	if request.method == 'GET':
		return render_template('users/accept.html')
	else:
		if request.form['acceptance'] == 'accept':
			current_user.status = 'CONFIRMED'
			flash('You have successfully confirmed your invitation to {0}'.format(settings.HACKATHON_NAME))
		else:
			current_user.status = 'REJECTED'
		DB.session.add(current_user)
		DB.session.commit()