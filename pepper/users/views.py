from flask.ext.login import login_user, logout_user, current_user, login_required
from flask import request, render_template, redirect, url_for, flash
import requests
from models import User, UserRole
from pepper.app import DB
from sqlalchemy.exc import IntegrityError
from pepper import settings
import urllib2
from pepper.utils import s3, send_email, s, roles_required, hs_client
from helpers import send_status_change_notification
import keen

def landing():
	if current_user.is_authenticated:
		return redirect(url_for('dashboard'))
	return render_template("static_pages/index.html")

def login():
	return redirect(
		'https://my.mlh.io/oauth/authorize?client_id={0}&redirect_uri={1}callback&response_type=code'.format(
			settings.MLH_APPLICATION_ID, urllib2.quote(settings.BASE_URL)))

@login_required
def logout():
	logout_user()
	return redirect(url_for('landing'))

def callback():
	url = 'https://my.mlh.io/oauth/token?client_id={0}&client_secret={1}&code={2}&redirect_uri={3}callback&grant_type=authorization_code'.format(
		settings.MLH_APPLICATION_ID, settings.MLH_SECRET, request.args.get('code'),
		urllib2.quote(settings.BASE_URL, ''))
	print url
	resp = requests.post(url)
	access_token = resp.json()['access_token']
	user = User.query.filter_by(access_token=access_token).first()
	if user is None:  # create the user
		try:
			user_info = requests.get('https://my.mlh.io/api/v1/user?access_token={0}'.format(access_token)).json()
			user_info['type'] = 'MLH'
			user_info['access_token'] = access_token
			user = User.query.filter_by(email=user_info['data']['email']).first()
			if user is None:
				user = User(user_info)
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
def confirm_registration():
	if request.method == 'GET':
		if current_user.status != 'NEW':
			return redirect(url_for('dashboard'))
		return render_template('users/confirm.html', user=current_user)
	else:
		skill_level = request.form.get('skill-level')
		num_hackathons = request.form.get('num-hackathons')
		interests = request.form.get('interests')
		race_list = request.form.getlist('race')
		if None in (skill_level, num_hackathons, interests, race_list):
			flash('You must fill out the required fields', 'error')
			return redirect(request.url)
		current_user.skill_level = skill_level
		current_user.num_hackathons = num_hackathons
		current_user.interests = interests
		current_user.race = 'NO_DISCLOSURE' if 'NO_DISCLOSURE' in race_list else ','.join(race_list)
		if 'resume' in request.files:
			resume = request.files['resume']
			if is_pdf(resume.filename):  # if pdf upload to AWS
				s3.Object(settings.S3_BUCKET_NAME, 'resumes/{0}, {1} ({2}).pdf'.format(current_user.lname, current_user.fname, current_user.hashid)).put(Body=resume)
			else:
				flash('Resume must be in PDF format', 'error')
				return redirect(request.url)
		else:
			flash('Please upload your resume', 'error')
			return redirect(request.url)
		current_user.status = 'PENDING'
		DB.session.add(current_user)
		DB.session.commit()

		# keen.add_event('sign_ups', {
		# 	'created_at'
		# })

		# send a confirmation email
		html = render_template('emails/applied.html', user=current_user)
		send_email(settings.GENERAL_INFO_EMAIL, 'Thank you for applying to {0}'.format(settings.HACKATHON_NAME), current_user.email, txt_content=None, html_content=html)
		flash(
			'Congratulations! You have successfully applied for {0}! You should receive a confirmation email shortly'.format(
				settings.HACKATHON_NAME), 'success')
		return redirect(url_for('dashboard'))


def update_user_data():
	user_info = requests.get('https://my.mlh.io/api/v1/user?access_token={0}'.format(current_user.access_token)).json()
	current_user.email = user_info['data']['email']
	current_user.fname = user_info['data']['first_name']
	current_user.lname = user_info['data']['last_name']
	# current_user.class_standing = DB.Column(DB.String(255))
	current_user.major = user_info['data']['major']
	current_user.shirt_size = user_info['data']['shirt_size']
	current_user.dietary_restrictions = user_info['data']['dietary_restrictions']
	current_user.birthday = user_info['data']['date_of_birth']
	current_user.gender = user_info['data']['gender']
	current_user.phone_number = user_info['data']['phone_number']
	current_user.school = user_info['data']['school']['name']
	current_user.special_needs = user_info['data']['special_needs']
	DB.session.add(current_user)
	DB.session.commit()


@login_required
def dashboard():
	if current_user.type == 'corporate':
		return redirect(url_for('corp-dash'))
	if current_user.status == 'NEW':
		update_user_data()
		return redirect(url_for('confirm-registration'))
	elif current_user.status == 'ACCEPTED':
		return redirect(url_for('accept-invite'))
	elif current_user.status == 'CONFIRMED':
		return render_template('users/dashboard/confirmed.html', user=current_user)
	elif current_user.status == 'DECLINED':
		return render_template('users/dashboard/declined.html', user=current_user)
	elif current_user.status == 'REJECTED':
		return render_template('users/dashboard/rejected.html', user=current_user)
	elif current_user.status == 'WAITLISTED':
		return render_template('users/dashboard/waitlisted.html', user=current_user)
	elif current_user.status == 'ADMIN':
		users = User.query.order_by(User.created.asc())
		return render_template('users/dashboard/admin_dashboard.html', user=current_user, users=users)
	return render_template('users/dashboard/pending.html', user=current_user)


def is_pdf(filename):
	return '.' in filename and filename.lower().rsplit('.', 1)[1] == 'pdf'


@login_required
def accept():
	if current_user.status != 'ACCEPTED':  # they aren't allowed to accept their invitation
		message = {
			'NEW': "You haven't completed your application for {0}! Please submit your application before visiting this page!".format(settings.HACKATHON_NAME),
			'PENDING': "You haven't been accepted to {0}! Please wait for your invitation before visiting this page!".format(
				settings.HACKATHON_NAME),
			'CONFIRMED': "You've already accepted your invitation to {0}! We look forward to seeing you here!".format(
				settings.HACKATHON_NAME),
			'REJECTED': "You've already rejected your {0} invitation. Unfortunately, for space considerations you cannot change your response.".format(
				settings.HACKATHON_NAME),
			None: "Corporate users cannot view this page."
		}
		flash(message[current_user.status], 'error')
		return redirect(url_for('dashboard'))
	if request.method == 'GET':
		if current_user.med_auth_signature_id is None: # Generate the medical authorization waiver
			med_signature_request = hs_client.send_signature_request_embedded_with_template(
				test_mode=settings.DEBUG,
				client_id=settings.HELLO_SIGN_CLIENT_ID,
				template_id=settings.HELLO_SIGN_MED_WAIVER_TEMPLATE_ID,
				subject='Medical Authorization for {0} - {1} {2}'.format(settings.HACKATHON_NAME, current_user.fname, current_user.lname),
				message='Please sign the medical authorization waiver for UT Austin',
				signers=[
					{'role_name': 'Attendee', 'email_address': current_user.email, 'name': '{0} {1}'.format(current_user.fname, current_user.lname)}
				]
			)
			current_user.med_auth_signature_id = med_signature_request.signatures[0].signature_id
		if current_user.waiver_signature_id is None:
			waiver_signature_request = hs_client.send_signature_request_embedded_with_template(
				test_mode=settings.DEBUG,
				client_id=settings.HELLO_SIGN_CLIENT_ID,
				template_id=settings.HELLO_SIGN_WAIVER_TEMPLATE_ID,
				subject='Release Waiver for {0} - {1} {2}'.format(settings.HACKATHON_NAME, current_user.fname,
																		 current_user.lname),
				message='Please sign the release waiver for UT Austin',
				signers=[
					{'role_name': 'Attendee', 'email_address': current_user.email,
					 'name': '{0} {1}'.format(current_user.fname, current_user.lname)}
				]
			)
			current_user.waiver_signature_id = waiver_signature_request.signatures[0].signature_id

		DB.session.add(current_user)
		DB.session.commit()
		med_waiver_url = hs_client.get_embedded_object(current_user.med_auth_signature_id).sign_url
		release_waiver_url = hs_client.get_embedded_object(current_user.waiver_signature_id).sign_url
			# for signature in med_signature_request.signatures:
			# 	embedded_obj = hs_client.get_embedded_object(signature.signature_id)
			# 	sign_url = embedded_obj.sign_url
		return render_template('users/accept.html', user=current_user, sign_url=release_waiver_url)
	else:
		if 'accept' in request.form: #User has accepted the invite
			# if 'resume' in request.files:
			# 	resume = request.files['resume']
			# 	if is_pdf(resume.filename):  # if pdf upload to AWS
			# 		s3.Object('hacktx-pepper', 'resumes/{0}-{1}-{2}.pdf'.format(current_user.id, current_user.lname,
			# 																  current_user.fname)).put(Body=resume)
			# 		current_user.resume_uploaded = True
			# 	else:
			# 		flash('Resume must be in PDF format')
			# 		return redirect(url_for('accept-invite'))
			current_user.status = 'CONFIRMED'
			flash('You have successfully confirmed your invitation to {0}'.format(settings.HACKATHON_NAME))
		else:
			current_user.status = 'DECLINED'
		DB.session.add(current_user)
		DB.session.commit()
		return redirect(url_for('dashboard'))


@login_required
@roles_required('admin')
def create_corp_user():
	if request.method == 'GET':
		return render_template('users/admin/create_user.html')
	else:
		# Build a user based on the request form
		user_data = {'fname': request.form['fname'],
					 'lname': request.form['lname'],
					 'email': request.form['email']}
		user_data['type'] = 'corporate'
		user = User(user_data)
		DB.session.add(user)
		DB.session.commit()

		# send invite to the recruiter
		token = s.dumps(user.email)
		url = url_for('new-user-setup', token=token, _external=True)
		txt = render_template('emails/pre_inline/../templates/emails/corporate_welcome.txt', user=user, setup_url=url)
		html = render_template('emails/pre_inline/../templates/emails/corporate_welcome.html', user=user, setup_url=url)

		try:
			print txt
			if not send_email(from_email=settings.GENERAL_INFO_EMAIL,
							  subject='Your invitation to join my{}'.format(settings.HACKATHON_NAME),
							  to_email=user.email, txt_content=txt, html_content=html):
				print 'Failed to send message'
				flash('Unable to send message to recruiter', 'error')
		except ValueError as e:
			print e
		flash('You successfully create a new recruiter account.', 'success')
		return render_template('users/admin/create_user.html')


@login_required
@roles_required('admin')
def batch_modify():
	if request.method == 'GET':
		return 'Batch modify page'
	else:
		modify_type = request.form.get('type')
		if modify_type == 'fifo':
			accepted_attendees = User.query.filter_by(status='PENDING')  # TODO: limit by x
		else:  # randomly select n users out of x users
			x = request.form.get('x') if request.form.get(
				'x') is not 0 else -1  # TODO it's the count of users who are pending
			random_pool = User.query.filter
		# TODO: figure out how to find x random numbers


@login_required
@roles_required('admin')
def modify_user(hashid):
	# Send a post request that changes the user state to rejected or accepted
	user = User.get_with_hashid(hashid)
	user.status == request.form.get('status')
	DB.session.add(user)
	DB.session.commit()

	send_status_change_notification(user)


# Developers can use this portal to log into any particular user when debugging
def debug_user():
	if settings.DEBUG:
		if current_user.is_authenticated:
			logout_user()
		if request.method == 'GET':
			return render_template('users/admin/internal_login.html')
		else:
			id = request.form['id']
			user = User.query.filter_by(id=id).first()
			if user is None:
				return 'User does not exist'
			login_user(user, remember=True)
			return redirect(url_for('landing'))
	else:
		return 'Disabled internal debug mode'


def initial_create():
	user_count = User.query.count()
	if user_count == 0:
		if request.method == 'GET':
			return render_template('users/admin/initial_create.html')
		else:
			user_info = {
				'email': request.form.get('email'),
				'fname': request.form.get('fname'),
				'lname': request.form.get('lname'),
				'password': request.form.get('password'),
				'type': 'admin'
			}
			user = User(user_info)
			user.status = 'ADMIN'
			DB.session.add(user)
			DB.session.commit()

			# add admin role to the user
			role = UserRole(user.id)
			role.name = 'admin'
			DB.session.add(role)
			DB.session.commit()

			return 'Successfully created initial admin user'
	else:
		return 'Cannot create new admin'
