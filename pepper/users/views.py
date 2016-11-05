from flask.ext.login import login_user, logout_user, current_user, login_required
from flask import request, render_template, redirect, url_for, flash, g, jsonify, make_response, render_template_string
import requests
from models import User, UserRole
from pepper.app import DB
from sqlalchemy.exc import IntegrityError
from pepper import settings
import urllib2
from pepper.utils import s3, send_email, s, roles_required, ts, calculate_age
from helpers import send_status_change_notification, check_password, hash_pwd, send_recruiter_invite
import keen
from datetime import datetime
from pytz import timezone
from pepper.legal.models import Waiver
import random
from sqlalchemy import or_, and_
import urllib


cst = timezone('US/Central')


def landing():
	if current_user.is_authenticated:
		return redirect(url_for('dashboard'))
	return render_template("static_pages/index.html")


def login():
	return redirect(
		'https://my.mlh.io/oauth/authorize?client_id={0}&redirect_uri={1}callback&response_type=code'.format(
			settings.MLH_APPLICATION_ID, urllib2.quote(settings.BASE_URL)))


def login_local():
	if request.method == 'GET':
		if current_user.is_authenticated:
			return redirect(url_for('dashboard'))
		return render_template('users/login.html')
	else:
		email = request.form['email']
		password = request.form['password']
		user = User.query.filter_by(email=email).first()
		if user is None:
			flash("We couldn't find an account related with this email. Please verify the email entered.", "warning")
			return redirect(url_for('login_local'))
		elif user.password is None:
			flash('This account has not been setup yet. Please click the login link in your setup email.')
			return redirect(url_for('login_local'))
		elif not check_password(user.password, password):
			flash("Invalid Password. Please verify the password entered.", 'warning')
			return redirect(url_for('login_local'))

		user_role = UserRole.query.filter_by(user_id=user.id).first()
		if user_role is not None:
			flash("Invalid login portal, please login in again")
			return redirect(url_for('corp-login'))

		login_user(user, remember=True)
		flash('Logged in successfully!', 'success')
		return redirect(url_for('dashboard'))


def register_local():
	if not settings.REGISTRATION_OPEN:
		flash('Registration is currently closed', 'error')
		return redirect(url_for('landing'))
	if not settings.FALLBACK_LOCAL_REGISTER:
		flash('Sign up through MyMLH', 'error')
		return redirect(url_for('landing'))
	if request.method == 'GET':
		return render_template('users/register_local.html')
	else: # Local registration
		user_info = {
				'email': request.form.get('email'),
				'first_name': request.form.get('fname'),
				'last_name': request.form.get('lname'),
				'password': request.form.get('password'),
				'type': 'local',
				'date_of_birth': request.form.get('date_of_birth'),
				'major': request.form.get('major'),
				'shirt_size': request.form.get('shirt_size'),
				'dietary_restrictions': request.form.get('dietary_restrictions'),
				'gender': request.form.get('gender'),
				'phone_number': request.form.get('phone_number'),
				'special_needs': request.form.get('special_needs'),
				'school_name': request.form.get('school_name')
		}

		if request.form.get('gender_other') != '' and user_info['gender'] == 'Other':
			user_info['gender'] = request.form.get('gender_other')
		
		user = User.query.filter_by(email=user_info['email']).first()
		if user is None:  # create the user
			g.log.info('Creating a user')
			g.log = g.log.bind(email=user_info['email'])
			g.log.info('Creating a new user from local information')
			user = User(user_info)
			DB.session.add(user)
			DB.session.commit()
			g.log.info('Successfully created user')

			token = s.dumps(user.email)
			url = url_for('confirm-account', token=token, _external=True)
			html = render_template('emails/confirm_account.html', link=url, user=user)
			send_email(settings.GENERAL_INFO_EMAIL, 'Confirm Your Account', user.email, None, html)
			login_user(user, remember=True)
		else: # Admin/Corporate need to login in from a different page
			flash('The account already exists, please login again', 'error')
			return redirect(url_for('login_local'))

		return redirect(url_for('confirm-registration'))


@login_required
def edit_profile():
	if request.method == 'GET':
		if current_user.type == 'MLH':
			return redirect("https://my.mlh.io/edit")
		elif current_user.type == 'local':
			return render_template('users/edit_profile.html', user=current_user)
	else:
		updated_user_info = {
				'email': request.form.get('email'),
				'first_name': request.form.get('fname'),
				'last_name': request.form.get('lname'),
				'password': request.form.get('new_password'),
				'type': 'local',
				'date_of_birth': request.form.get('date_of_birth'),
				'major': request.form.get('major'),
				'shirt_size': request.form.get('shirt_size'),
				'dietary_restrictions': request.form.get('dietary_restrictions'),
				'gender': request.form.get('gender'),
				'phone_number': request.form.get('phone_number'),
				'special_needs': request.form.get('special_needs'),
				'school_name': request.form.get('school_name')
		}
		if request.form.get('new_password') == '':
			updated_user_info['password'] = request.form.get('old_password')
		if not check_password(current_user.password, request.form.get('old_password')):
			flash('Profile update failed because of invalid Password. Please verify the password entered.', 'warning')
			return render_template('users/confirm.html', user=current_user)
		else:
			if request.form.get('gender_other') != '' and updated_user_info['gender'] == 'Other':
				updated_user_info['gender'] = request.form.get('gender_other')
			update_user_data('local', local_updated_info=updated_user_info)
			flash('Profile updated!', 'success')
			return redirect(url_for('dashboard'))


@login_required
def logout():
	logout_user()
	return redirect(url_for('landing'))


def callback():
	url = 'https://my.mlh.io/oauth/token'
	body = {
		'client_id': settings.MLH_APPLICATION_ID,
		'client_secret': settings.MLH_SECRET,
		'code': request.args.get('code'),
		'grant_type': 'authorization_code',
		'redirect_uri': settings.BASE_URL + "callback"
	}
	resp = requests.post(url, json=body)
	try:
		json = resp.json()
	except Exception as e:
		g.log = g.log.bind(error=e, response=resp)
		g.log.error('Error Decoding JSON')
	
	if resp.status_code == 401: # MLH sent expired token
		redirect_url = 'https://my.mlh.io/oauth/authorize?client_id={0}&redirect_uri={1}callback&response_type=code'.format(
			settings.MLH_APPLICATION_ID, urllib2.quote(settings.BASE_URL))
		
		g.log = g.log.bind(auth_code=request.args.get('code'), http_status=resp.status_code, resp=resp.text, redirect_url=redirect_url)
		g.log.error('Got expired auth code, redirecting: ')
		if settings.FALLBACK_LOCAL_REGISTER: # If our fallback is to request a new MLH code
			g.log.info('Redirecting user to local registration')
			return redirect(url_for('register_local'))
		else:
			g.log.info('Requesting a new auth code from MLH')
			return redirect(redirect_url)

	if 'access_token' in json:
		access_token = json['access_token']
	else: # This is VERY bad, we should never hit this error
		g.log = g.log.bind(auth_code=request.args.get('code'), http_status=resp.status_code, resp=resp.text, body=body)
		g.log.error('URGENT: FAILED BOTH MLH AUTH CODE CHECKS')
		return render_template('layouts/error.html', title='MLH Server Error', message="We're having trouble pulling your information from MLH servers. This is a fatal error. Please contact {} for assistance".format(settings.GENERAL_INFO_EMAIL)), 505


	user = User.query.filter_by(access_token=access_token).first()
	if user is None:  # create the user
		try:
			g.log.info('Creating a user')
			user_info = requests.get('https://my.mlh.io/api/v1/user?access_token={0}'.format(access_token)).json()
			user_info['type'] = 'MLH'
			user_info['access_token'] = access_token
			g.log = g.log.bind(email=user_info['data']['email'])
			user = User.query.filter_by(email=user_info['data']['email']).first()
			if user is None:
				if settings.REGISTRATION_OPEN:
					g.log.info('Creating a new user from MLH info')
					user = User(user_info)
				else:
					flash('Registration is currently closed', 'error')
					return redirect(url_for('landing'))
			else:
				user.access_token = access_token
			DB.session.add(user)
			DB.session.commit()
			g.log.info('Successfully created user')
			login_user(user, remember=True)
		except IntegrityError:
			# a unique value already exists this should never happen
			DB.session.rollback()
			flash('A fatal error occurred. Please contact us for help', 'error')
			return render_template('static_pages/index.html')
		except Exception:
			g.log.error('Unable to create the user')
	else:
		login_user(user, remember=True)
		return redirect(url_for('dashboard'))
	return redirect(url_for('confirm-registration'))


def confirm_account(token):
	try:
		email = s.loads(token)
		user = User.query.filter_by(email=email).first()
		user.confirmed = True
		DB.session.add(user)
		DB.session.commit()
		flash('Successfully confirmed account', 'success')
		return redirect(url_for('confirm-registration'))
	except:
		return render_template('layouts/error.html', message="That's an invalid link. Please contact {} for help.".format(settings.GENERAL_INFO_EMAIL)), 401


@login_required
def confirm_registration():
	if not settings.REGISTRATION_OPEN:
		g.log = g.log.bind(email=current_user.email, access_token=current_user.access_token)
		g.log.info('Applications closed user redirected to homepage')
		flash('Registration is currently closed', 'error')
		logout_user()
		return redirect(url_for('landing'))
	if request.method == 'GET':
		if current_user.status != 'NEW':
			return redirect(url_for('dashboard'))
		elif current_user.confirmed == False:
			return render_template('layouts/error.html', title='Confirm Account', message='Please check your email to confirm your account before proceeding'), 403
		return render_template('users/confirm.html', user=current_user)
	else:
		skill_level = request.form.get('skill-level')
		num_hackathons = request.form.get('num-hackathons')
		try:
			if int(num_hackathons) > 9223372036854775807:
				flash("{} seems like a lot of hackathons! I don't think you've been to that many".format(num_hackathons), 'error')
				return redirect(request.url)
		except ValueError:
			flash('Please enter a number in number of hackathons', 'error')
			return redirect(request.url)

		interests = request.form.get('interests')
		race_list = request.form.getlist('race')
		class_standing = request.form.get('class-standing')
		if request.form.get('mlh') != 'TRUE':
			flash('You must agree to MLH data sharing', 'error')
			return redirect(request.url)
		if None in (skill_level, num_hackathons, interests, race_list, class_standing):
			flash('You must fill out the required fields', 'error')
			return redirect(request.url)
		current_user.skill_level = skill_level
		current_user.num_hackathons = num_hackathons
		current_user.interests = interests
		current_user.race = 'NO_DISCLOSURE' if 'NO_DISCLOSURE' in race_list else ','.join(race_list)
		current_user.class_standing = class_standing
		current_user.time_applied = datetime.utcnow()
		if 'resume' in request.files:
			resume = request.files['resume']
			if is_pdf(resume.filename):  # if pdf upload to AWS
				s3.Object(settings.S3_BUCKET_NAME, u'resumes/{0}, {1} ({2}).pdf'.format(current_user.lname, current_user.fname, current_user.hashid)).put(Body=resume)
			else:
				flash('Resume must be in PDF format', 'error')
				return redirect(request.url)
		else:
			flash('Please upload your resume', 'error')
			return redirect(request.url)
		current_user.status = 'PENDING'
		DB.session.add(current_user)
		DB.session.commit()
		g.log = g.log.bind(email=current_user.email)
		g.log.info('User successfully applied')
		fmt = '%Y-%m-%dT%H:%M:%S.%f'
		keen.add_event('sign_ups', {
			'date_of_birth': current_user.birthday.strftime(fmt),
			'dietary_restrictions': current_user.dietary_restrictions,
			'email': current_user.email,
			'first_name': current_user.fname,
			'last_name': current_user.lname,
			'gender': current_user.gender,
			'id': current_user.id,
			'major': current_user.major,
			'phone_number': current_user.phone_number,
			'school': {
				'id': current_user.school_id,
				'name': current_user.school_name
			},
			'keen': {
				'timestamp': current_user.time_applied.strftime(fmt)
			},
			'interests': interests,
			'skill_level': skill_level,
			'races': race_list,
			'num_hackathons': num_hackathons,
			'class_standing': class_standing,
			'shirt_size': current_user.shirt_size,
			'special_needs': current_user.special_needs
		})

		# send a confirmation email
		html = render_template('emails/applied.html', user=current_user)
		send_email(settings.GENERAL_INFO_EMAIL, 'Thank you for applying to {0}'.format(settings.HACKATHON_NAME), current_user.email, txt_content=None, html_content=html)
		g.log.info('Successfully sent a confirmation email')

		flash('Congratulations! You have successfully applied for {0}! You should receive a confirmation email shortly'.format(settings.HACKATHON_NAME), 'success')

		return redirect(url_for('dashboard'))


@login_required
@roles_required('admin')
def check_in_manual():
	if request.method == 'GET':
		return render_template('users/admin/check_in.html')
	else:
		email = request.form.get('email')
		user = User.query.filter_by(email=email).first()
		age = calculate_age(user.birthday)
		if age < 18 or user.status != 'CONFIRMED' or user.checked_in:
			if age < 18:
				flash('User under 18', 'error')
			if user.status != 'CONFIRMED':
				flash('User not confirmed', 'error')
			if user.checked_in:
				flash('User is already checked in', 'error')
			return render_template('layouts/error.html',
								   message="Unable to check in user"), 401
		return render_template('users/admin/confirm_check_in.html', user=user, age=age)

def check_in_post():
	email = request.form.get('email')
	user = User.query.filter_by(email=email).first()
	user.checked_in = True
	DB.session.commit()
	fmt = '%Y-%m-%dT%H:%M:%S.%f'
	keen.add_event('check_in', {
		'date_of_birth': user.birthday.strftime(fmt),
		'dietary_restrictions': user.dietary_restrictions,
		'email': user.email,
		'first_name': user.fname,
		'last_name': user.lname,
		'gender': user.gender,
		'id': user.id,
		'major': user.major,
		'phone_number': user.phone_number,
		'school': {
			'id': user.school_id,
			'name': user.school_name
		},
		'keen': {
			'timestamp': user.time_applied.strftime(fmt)
		},
		'interests': user.interests,
		'skill_level': user.skill_level,
		'races': user.race,
		'num_hackathons': user.num_hackathons,
		'class_standing': user.class_standing,
		'shirt_size': user.shirt_size,
		'special_needs': user.special_needs
	})
	flash('Checked in {0} {1}'.format(user.fname, user.lname), 'success')
	return redirect(url_for('manual-check-in'))


def forgot_password():
	if request.method == 'GET':
		return render_template('users/forgot_password.html')
	else:
		email = request.form.get('email')
		user = User.query.filter_by(email=email).first()
		if user:
			token = ts.dumps(user.email, salt='recover-key')
			url = url_for('reset-password', token=token, _external=True)
			html = render_template('emails/reset_password.html', user=user, link=url)
			txt = render_template('emails/reset_password.txt', user=user, link=url)
			send_email('hello@hacktx.com', 'Your password reset link', email, txt, html)
		flash('If there is a registered user with {email}, then a password reset email has been sent!', 'success')
		return redirect(url_for('login_local'))


def reset_password(token):
	try:
		email = ts.loads(token, salt='recover-key', max_age=86400)
		user = User.query.filter_by(email=email).first()
	except:
		return render_template('layouts/error.html', error="That's an invalid link"), 401

	if request.method == 'GET':
		# find the correct user and log them in then prompt them for new password
		return render_template('users/reset_password.html')
	else:
		# take the password they've submitted and change it accordingly
		if user:
			if request.form.get('password') == request.form.get('password-check'):
				user.password = hash_pwd(request.form['password'])
				DB.session.add(user)
				DB.session.commit()
				login_user(user, remember=True)
				flash('Succesfully changed password!', 'success')
				return redirect(url_for('dashboard'))
			else:
				flash('You need to enter the same password in both fields!', 'error')
				return redirect(url_for('reset-password'), token=token)
		else:
			flash('Failed to reset password. This is an invalid link. Please contact us if this error persists', 'error')
			return redirect(url_for('forgot-password'))


def set_mlh_id():
	if request.method == 'GET':
		return render_template('users/admin/set_mlh_id.html')
	else:
		mlh_users = User.query.filter_by(type='MLH')
		i = 0
		for user in mlh_users:
			if user.access_token is not None:
				user_info = requests.get('https://my.mlh.io/api/v1/user?access_token={0}'.format(user.access_token)).json()
				if 'data' in user_info:
					user.mlh_id = user_info['data']['id']
					DB.session.add(user)
					DB.session.commit()
			i+=1
			print i

		return 'Finished updating ids'

def update_user_data(type, local_updated_info=None):
	if type == 'MLH':
		user_info = requests.get('https://my.mlh.io/api/v1/user?access_token={0}'.format(current_user.access_token)).json()
		if 'data' in user_info:
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
			current_user.school_id = user_info['data']['school']['id']
			current_user.school_name = user_info['data']['school']['name']
			current_user.special_needs = user_info['data']['special_needs']
			DB.session.add(current_user)
			DB.session.commit()
	elif type == 'local' and local_updated_info is not None:
			current_user.email = local_updated_info['email']
			current_user.fname = local_updated_info['first_name']
			current_user.lname = local_updated_info['last_name']
			current_user.major = local_updated_info['major']
			current_user.shirt_size = local_updated_info['shirt_size']
			current_user.dietary_restrictions = local_updated_info['dietary_restrictions']
			current_user.birthday = local_updated_info['date_of_birth']
			current_user.gender = local_updated_info['gender']
			current_user.phone_number = local_updated_info['phone_number']
			current_user.school_name = local_updated_info['school_name']
			current_user.special_needs = local_updated_info['special_needs']
			current_user.password = hash_pwd(local_updated_info['password'])
			DB.session.add(current_user)
			DB.session.commit()


@login_required
def dashboard():
	if request.method == 'GET':
		if current_user.type == 'corporate':
			return redirect(url_for('corp-dash'))
		if current_user.status == 'NEW':
			update_user_data('MLH')
			return redirect(url_for('confirm-registration'))
		elif current_user.status == 'ACCEPTED':
			return redirect(url_for('accept-invite'))
		elif current_user.status == 'SIGNING':
			return redirect(url_for('sign'))
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


@login_required
def refresh_from_MLH():
	user_info = requests.get('https://my.mlh.io/api/v1/user?access_token={0}'.format(current_user.access_token)).json()
	if 'data' in user_info:
		current_user.dietary_restrictions = user_info['data']['dietary_restrictions']
		current_user.special_needs = user_info['data']['special_needs']
		DB.session.add(current_user)
		DB.session.commit()
		return jsonify(dietary_restrictions=current_user.dietary_restrictions, special_needs=current_user.special_needs)
	else:
		response = jsonify(error='Unable to communicate with MLH')
		response.status_code = 503
		return response


@login_required
def edit_resume():
	if current_user.status == 'NEW':
		return redirect(url_for('dashboard'))
	if request.method == 'GET':
		# render template for editing resume
		return render_template('users/dashboard/update_resume.html', user=current_user)
	else:
		# Update your resume
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
		flash('You successfully updated your resume', 'success')
		return redirect(request.url)


@login_required
def view_own_resume():
	data_object = s3.Object(settings.S3_BUCKET_NAME,
							'resumes/{0}, {1} ({2}).pdf'.format(current_user.lname, current_user.fname, current_user.hashid)).get()
	response = make_response(data_object['Body'].read())
	response.headers['Content-Type'] = 'application/pdf'
	return response


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
		if current_user.status in message:
			flash(message[current_user.status], 'error')
		return redirect(url_for('dashboard'))
	if request.method == 'GET':
		return render_template('users/accept.html', user=current_user)
	else:
		if 'accept' in request.form: #User has accepted the invite
			current_user.status = 'SIGNING'
			flash('You have successfully confirmed your invitation to {0}'.format(settings.HACKATHON_NAME))
		else:
			current_user.status = 'DECLINED'
		DB.session.add(current_user)
		DB.session.commit()
		user_decision = 'confirmed' if current_user.status == 'SIGNING' else 'declined'
		fmt = '%Y-%m-%dT%H:%M:%S.%f'
		keen.add_event(user_decision, {
			'date_of_birth': current_user.birthday.strftime(fmt),
			'dietary_restrictions': current_user.dietary_restrictions,
			'email': current_user.email,
			'first_name': current_user.fname,
			'last_name': current_user.lname,
			'gender': current_user.gender,
			'id': current_user.id,
			'major': current_user.major,
			'phone_number': current_user.phone_number,
			'school': {
				'id': current_user.school_id,
				'name': current_user.school_name
			},
			'skill_level': current_user.skill_level,
			'races': current_user.race.split(','),
			'num_hackathons': current_user.num_hackathons,
			'class_standing': current_user.class_standing,
			'shirt_size': current_user.shirt_size,
			'special_needs': current_user.special_needs
		})
		return redirect(url_for('dashboard'))


@login_required
def sign():
	date_fmt = '%B %d, %Y'
	if current_user.status != 'SIGNING':  # they aren't allowed to accept their invitation
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
		if current_user.status in message:
			flash(message[current_user.status], 'error')
		return redirect(url_for('dashboard'))
	if request.method == 'GET':
		today = datetime.now(cst).date()
		return render_template('users/sign.html', user=current_user, date=today.strftime(date_fmt))
	else:
		relative_name = request.form.get('relative_name')
		relative_email = request.form.get('relative_email')
		relative_num = request.form.get('relative_num')

		allergies = request.form.get('allergies')
		medications = request.form.get('medications')
		special_health_needs = request.form.get('special_health_needs')

		medical_signature = request.form.get('medical_signature')
		medical_date = request.form.get('medical_date')

		indemnification_signature = request.form.get('indemnification_signature')
		indemnification_date = request.form.get('indemnification_date')

		photo_signature = request.form.get('photo_signature')
		photo_date = request.form.get('photo_date')

		ut_eid = request.form.get('ut_eid')

		if None in (relative_name, relative_email, relative_num, medical_signature, medical_date, indemnification_signature, indemnification_date, photo_signature, photo_date):
			flash('Must fill all required fields', 'error')
			return redirect(request.url)
		if current_user.school_id == 23:
			if ut_eid == None:
				flash('Must fill out UT EID')
				return redirect(request.url)
		signed_info = dict()
		for key in ('relative_name', 'relative_email', 'relative_num', 'allergies', 'medications', 'special_health_needs', 'medical_signature', 'indemnification_signature', 'photo_signature', 'ut_eid'):
			signed_info[key] = locals()[key]

		for key in ('medical_date', 'indemnification_date', 'photo_date'):
			signed_info[key] = datetime.strptime(locals()[key], date_fmt)
		signed_info['user_id'] = current_user.id
		waiver_info = Waiver(signed_info)
		DB.session.add(waiver_info)
		DB.session.commit()

		current_user.status = 'CONFIRMED'
		DB.session.add(current_user)
		DB.session.commit()

		fmt = '%Y-%m-%dT%H:%M:%S.%f'
		keen.add_event('waivers_signed', {
			'date_of_birth': current_user.birthday.strftime(fmt),
			'dietary_restrictions': current_user.dietary_restrictions,
			'email': current_user.email,
			'first_name': current_user.fname,
			'last_name': current_user.lname,
			'gender': current_user.gender,
			'id': current_user.id,
			'major': current_user.major,
			'phone_number': current_user.phone_number,
			'school': {
				'id': current_user.school_id,
				'name': current_user.school_name
			},
			'skill_level': current_user.skill_level,
			'races': current_user.race.split(','),
			'num_hackathons': current_user.num_hackathons,
			'class_standing': current_user.class_standing,
			'shirt_size': current_user.shirt_size,
			'special_needs': current_user.special_needs
		})

		# send email saying that they are confirmed to attend
		html = render_template('emails/application_decisions/confirmed_invite.html', user=current_user)
		send_email(settings.GENERAL_INFO_EMAIL, "You're confirmed for {}".format(settings.HACKATHON_NAME), current_user.email, html_content=html)

		flash("You've successfully confirmed your invitation to {}".format(settings.HACKATHON_NAME), 'success')
		return redirect(url_for('dashboard'))


@login_required
@roles_required('admin')
def create_corp_user():
	if request.method == 'GET':
		unverified_users = User.query.filter(and_(User.type == 'corporate', User.password == None)).all()
		return render_template('users/admin/create_user.html', unverified=unverified_users)
	else:
		# Build a user based on the request form
		user_data = {'fname': request.form['fname'],
					 'lname': request.form['lname'],
					 'email': request.form['email'],
					 'type': 'corporate'}
		user = User(user_data)
		DB.session.add(user)
		DB.session.commit()
		g.log = g.log.bind(corp_user='{0} {1} <{2}>'.format(user_data['fname'], user_data['lname'], user_data['email']))
		g.log = g.log.bind(admin='{0} {1} <{2}>'.format(current_user.fname, current_user.lname, current_user.email))
		g.log.info('Created new corporate account')
		try:
			send_recruiter_invite(user)
		except Exception:
			flash('Unable to send recruiter invite', 'error')
		return render_template('users/admin/create_user.html')


@login_required
@roles_required('admin')
def resend_recruiter_invite():
	#TODO Get the recruiter email
	email = 'test@dhs2014.com'
	user = User.query.filter_by(email=email).first()
	try:
		send_recruiter_invite(user)
		return jsonify()
	except Exception as e:
		g.log = g.log.bind(error=e)
		g.log.error('Unable to resend recruiter email: ')
		return jsonify(), 501


@login_required
@roles_required('admin')
def batch_modify():
	if request.method == 'GET':
		users = User.query.filter_by(status='PENDING').order_by(User.time_applied.asc()).all()
		return render_template('users/admin/accept_users.html', users=users)
	else:
		g.log.info('Starting acceptances')
		modify_type = request.form.get('type')
		num_to_accept = int(request.form.get('num_to_accept'))
		if modify_type == 'fifo':
			accepted_attendees = User.query.filter_by(status='WAITLISTED').order_by(User.time_applied.asc()).limit(num_to_accept).all()
			for attendee in accepted_attendees:
				attendee.status = 'ACCEPTED'
				DB.session.commit()
				html = render_template('emails/application_decisions/accept_from_waitlist.html', user=attendee)
				send_email(settings.GENERAL_INFO_EMAIL, "You're In! {} Invitation".format(settings.HACKATHON_NAME), attendee.email, html_content=html)
				g.log = g.log.bind(email=attendee.email)
				g.log.info('Sent email to')
		else:  # randomly select n users out of x users
			random_pool = User.query.filter(or_(User.status=='PENDING', User.status=='WAITLISTED')).all()
			accepted = random.sample(set(random_pool), num_to_accept)
			for attendee in accepted:
				if attendee.status == 'PENDING':
					html = render_template('emails/application_decisions/accepted.html', user=attendee)
				else: # they got off waitlist
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
		# x = request.form.get('x') if request.form.get(
			# 	'x') is not 0 else -1  # TODO it's the count of users who are pending
		# TODO: figure out how to find x random numbers
		flash('Finished acceptances', 'success')
		g.log.info('Finished acceptances')
		return redirect(request.url)


@login_required
@roles_required('admin')
def send_email_to_users():
	if request.method == 'GET':
		return render_template('users/admin/send_email.html')
	else:
		statuses = request.form.getlist('status')
		users = User.query.filter(and_(User.status.in_(statuses), User.checked_in == 'true'))
		foo = users.all()
		content = request.form.get('content')
		lines = content.split('\r\n')
		msg_body = u""
		i = 0
		for line in lines:
			msg_body += u'<tr><td class="content-block">{}</td></tr>\n'.format(line)
		for user in users:
			html = render_template('emails/generic_message.html', content=msg_body)
			html = render_template_string(html, user=user)
			# html = render_template('emails/welcome.html', user=user)
			send_email(settings.GENERAL_INFO_EMAIL, request.form.get('subject'), user.email, html_content=html)
			print 'Sent Email' + str(i)
			i += 1
		flash('Successfully sent', 'success')
		return 'Done'

@login_required
@roles_required('admin')
def reject_users():
	if request.method == 'GET':
		return render_template('users/admin/reject_users.html')
	else:
		users = User.query.filter(and_(or_(User.status == 'WAITLISTED'), User.school_id == 23)).all()
		i = 0
		for user in users:
			html = render_template('emails/application_decisions/rejected.html', user=user)
			send_email(settings.GENERAL_INFO_EMAIL, "Update from HackTX", user.email, html_content=html)
			user.status = 'REJECTED'
			DB.session.add(user)
			DB.session.commit()
			print 'Rejected {}'.format(user.email)
			print i
			i += 1
		flash('Finished rejecting', 'success')
		return redirect(request.url)



@login_required
@roles_required('admin')
def modify_user():
	if request.method == 'GET':
		return render_template('users/admin/modify_user.html')
	else:
	# Send a post request that changes the user state to rejected or accepted
		id = int(request.form.get('id'))
		user = User.query.filter_by(id=id).first()
		if user.status == 'WAITLISTED':
			user.status = request.form.get('status')
			DB.session.add(user)
			DB.session.commit()

			html = render_template('emails/application_decisions/accept_from_waitlist.html', user=user)
			send_email(settings.GENERAL_INFO_EMAIL, "Congrats! Your HackTX Invitation", user.email, html_content=html)
			flash('Successfully accepted {0} {1}'.format(user.fname, user.lname), 'success')
		return redirect(request.url)

# Developers can use this portal to log into any particular user when debugging
def debug_user():
	if settings.DEBUG or (current_user.is_authenticated and current_user.status == 'ADMIN'):
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
