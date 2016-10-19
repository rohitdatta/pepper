from pepper.app import DB
from pepper.users import User
from flask import url_for, jsonify, request, Response
import json
import os
from pepper import settings
from pepper.utils import calculate_age

def schedule():
	SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
	json_url = os.path.join(SITE_ROOT, "../static/api", "schedule.json")
	data = json.load(open(json_url))
	return Response(json.dumps(data),  mimetype='application/json')

def schedule_day(day):
	SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
	if day == '1':
		json_url = os.path.join(SITE_ROOT, "../static/api", "schedule-1.json")
	else:
		json_url = os.path.join(SITE_ROOT, "../static/api", "schedule-2.json")
	data = json.load(open(json_url))
	return Response(json.dumps(data), mimetype='application/json')

def partner_list():
	SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
	json_url = os.path.join(SITE_ROOT, "../static/api", "partners.json")
	data = json.load(open(json_url))
	return Response(json.dumps(data),  mimetype='application/json')

def passbook():
	email = request.get_json()['email']
	user = User.query.filter_by(email=email).first()
	if user is None or user.status != 'CONFIRMED':
		data = {'success': False}
	else:
		data = {'success': True,
				'email': user.email,
				'name': '{0} {1}'.format(user.fname, user.lname),
				'school': user.school_name}
	return jsonify(data)

def check_in():
	# Check if secret token matches
	if request.method == 'GET':
		email = request.args.get('email')
		volunteer_email = request.args.get('volunteer_email')
	else:
		data = request.json
		email = data['email']
		volunteer_email = data['volunteer_email']

	# if data['secret'] != settings.CHECK_IN_SECRET:
	# 	message = 'Unauthorized'
	# 	return jsonify(message=message), 401

	# Get the user email and check them in
	user = User.query.filter_by(email=email).first()
	if user is not None:
		message = 'Found user'
		if request.method == 'POST':
			# check the user in
			if user.checked_in: # User is already checked in
				message = 'Attendee is already checked in'
			else:
				if user.status == 'CONFIRMED':
					user.checked_in = True
					DB.session.add(user)
					DB.session.commit()
					message = 'Attendee successfully checked in'
				else:
					message = 'Attendee has not been confirmed to attend {}'.format(settings.HACKATHON_NAME)
			# return back success to the check in app
	else:
		message = 'User does not exist'

	user_dict = {
		'name': "{0} {1}".format(user.fname, user.lname),
		'school': user.school_name,
		'email': user.email,
		'age': calculate_age(user.birthday),
		'checked_in': user.checked_in,
		'confirmed': user.status == 'CONFIRMED'
	}

	return jsonify(message=message, user=user_dict)