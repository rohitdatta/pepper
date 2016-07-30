from flask.ext.login import login_user, logout_user, current_user, login_required
from flask import request, render_template, redirect, url_for, flash
import requests
from models import User, Role
from mito.app import DB, sg
from sqlalchemy.exc import IntegrityError
from mito import settings
import sendgrid
from sendgrid.helpers.mail import *
import urllib2
import string, random
from flask_user import roles_required
from mito.utils import s3

def landing():
	if current_user.is_authenticated:
		return redirect(url_for('dashboard'))
	return render_template("static_pages/index.html")

def login():
	return redirect('https://my.mlh.io/oauth/authorize?client_id={0}&redirect_uri={1}callback&response_type=code'.format(settings.MLH_APPLICATION_ID, urllib2.quote(settings.BASE_URL)))

@login_required
def logout():
	logout_user()
	return redirect(url_for('landing'))

def callback():
	url = 'https://my.mlh.io/oauth/token?client_id={0}&client_secret={1}&code={2}&redirect_uri={3}callback&grant_type=authorization_code'.format(settings.MLH_APPLICATION_ID, settings.MLH_SECRET, request.args.get('code'), urllib2.quote(settings.BASE_URL, ''))
	print url
	resp = requests.post(url)
	access_token = resp.json()['access_token']
	user = User.query.filter_by(access_token=access_token).first()
	if user is None: # create the user
		try:
			user_info = requests.get('https://my.mlh.io/api/v1/user?access_token={0}'.format(access_token)).json()
			user_info['type'] = 'MLH'
			user_info['access_token'] = access_token
			user = User.query.filter_by(email=user_info['data']['email']).first()
			if user is None:
				user = User(user_info)
				user.roles.append(Role(name='attendee'))
			else:
				user.access_token = access_token
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
@roles_required('attendee')
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
def dashboard():
	if current_user.type == 'corporate':
		return redirect(url_for('corp-dash'))
	if current_user.status == 'ACCEPTED':
		return redirect(url_for('accept-invite'))
	elif current_user.status == 'CONFIRMED':
		return render_template('users/dashboard/confirmed.html')
	elif current_user.status == 'REJECTED':
		return render_template('users/dashboard/rejected.html', user=current_user)
	elif current_user.status == 'WAITLISTED':
		return render_template('users/dashboard/waitlisted.html', user=current_user)
	elif current_user.status == 'ADMIN':
		users = User.query.order_by(User.created.asc())
		return render_template('users/dashboard/admin_dashboard.html', user=current_user, users=users)
	return render_template('users/dashboard/pending.html', user=current_user)

def is_pdf(filename):
	return '.' in filename and (filename.rsplit('.', 1)[1] == 'pdf' or filename.rsplit('.', 1)[1] == 'PDF')

@login_required
@roles_required('attendee')
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
		# if request.form['acceptance'] == 'accept':
		if 'resume' in request.files:
			resume = request.files['resume']
			if is_pdf(resume.filename):  # if pdf upload to AWS
				s3.Object('hacktx-mito', 'resumes/{0}-{1}-{2}.pdf'.format(current_user.id, current_user.lname, current_user.fname)).put(Body=resume)
			else:
				flash('Resume must be in PDF format')
				return redirect(url_for('accept-invite'))
		current_user.status = 'CONFIRMED'
		flash('You have successfully confirmed your invitation to {0}'.format(settings.HACKATHON_NAME))
		# else:
		# 	current_user.status = 'REJECTED'
		DB.session.add(current_user)
		DB.session.commit()
		return redirect(url_for('dashboard'))

@login_required
@roles_required('admin')
def create_corp_user(): # TODO: require this to be an admin function
	if request.method == 'GET':
		return render_template('users/admin/create_corp.html')
	else:
		# Build a user based on the request form
		user_data = {'fname': request.form['fname'],
					 'lname': request.form['lname'],
					 'email': request.form['email']}
		user_data['password'] = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(50))
		user_data['type'] = 'corporate'
		user = User(user_data) # TODO: add the recruiter role here
		user.roles.append(Role(name='corp'))
		DB.session.add(user)
		DB.session.commit()

		# send invite to the recruiter # TODO: make this a reset password link
		data = {
			"content": [
				{
					"type": "text/plain",
					"value": "Welcome to HackTX! Here's your login info: Password: {0}".format(user_data['password'])
				}
			],
			"from": {
				"email": "partnerships@freetailhackers.com",
				"name": "Freetail Hackers"
			},
			"personalizations": [
				{
					"to": [
						{
							"email": user.email,
							"name": '{0} {1}'.format(user.fname, user.lname)
						}
					]
				}
			],
			"reply_to": {
				"email": "partnerships@freetailhackers.com",
				"name": "HackTX Team"
			},
			"subject": "Your invitation to join HackTX",
		}
		response = sg.client.mail.send.post(request_body=data)
		print response.status_code
		flash('You successfully create a new recruiter account.', 'success')
		return render_template('users/admin/create_corp.html')

def internal_login():
	if settings.DEBUG:
		if request.method == 'GET':
			return render_template('users/admin/internal_login.html')
		else:
			id = request.form['id']
			user = User.query.filter_by(id=id).first()
			login_user(user, remember=True)
			return redirect(url_for('landing'))
	else:
		return 'Disabled internal debug mode'