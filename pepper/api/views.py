import json
import os
import urllib
from datetime import datetime

from flask import jsonify, request, Response
import keen

from pepper import settings
from pepper.app import DB, csrf, worker_queue
from pepper.legal import Waiver
from pepper.users import User, batch
from pepper.utils import calculate_age
from pepper import status


def schedule():
    SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
    json_url = os.path.join(SITE_ROOT, "../static/api", "schedule.json")
    data = json.load(open(json_url))
    return Response(json.dumps(data), mimetype='application/json')


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
    return Response(json.dumps(data), mimetype='application/json')


@csrf.exempt
def passbook():
    email = request.get_json()['email']
    user = User.query.filter_by(email=email).first()
    if user is None or user.status != status.CONFIRMED:
        data = {'success': False}
    else:
        data = {'success': True,
                'email': user.email,
                'name': '{0} {1}'.format(user.fname, user.lname),
                'school': user.school_name}
    return jsonify(data)


@csrf.exempt
def check_in():
    if not settings.CHECK_IN_ENABLED:
        return jsonify(message='{} is over. This endpoint is closed'.format(settings.HACKATHON_NAME)), 405
    # Check if secret token matches
    if request.method == 'GET':
        email = urllib.unquote(request.args.get('email')).lower()
        #volunteer_email = urllib.unquote(request.args.get('volunteer_email'))
        secret = urllib.unquote(request.args.get('secret'))
    else:
        data = request.json
        print(data)
        email = data['email'].lower()
        #volunteer_email = data['volunteer_email']
        secret = data['secret']
        eid = data.get('eid')

    if secret != settings.CHECK_IN_SECRET:
        message = 'Unauthorized'
        return jsonify(message=message), 401


    # Get the user email and check them in
    # TODO: when emails are normalized to lowercase, do the same here
    matched_users = User.query.filter(User.email.ilike(email)).all()
    user = max(matched_users, key=lambda u: status.STATUS_LEVEL[u.status]) if matched_users else None
    if user is not None:
        waiver = Waiver.query.filter_by(user_id=user.id).first()
        requires_eid = user.school_id == 23 and waiver and not waiver.ut_eid
        message = 'Found user'
        bday = user.birthday
        if request.method == 'POST':
            # check the user in
            if user.checked_in:  # User is already checked in
                message = 'Attendee is already checked in'
            else:
                if user.status == status.CONFIRMED:
                    # we didn't sanitize schools, so some students slipped by without giving us their EIDs
                    if eid and requires_eid:
                        waiver.ut_eid = eid
                        DB.session.add(waiver)
                        DB.session.commit()
                        requires_eid = False
                    user.checked_in = True
                    DB.session.add(user)
                    DB.session.commit()
                    batch.keen_add_event(user.id, 'check_in', datetime.utcnow())
                    message = 'Attendee successfully checked in'
                else:
                    message = 'Attendee has not been confirmed to attend {}'.format(settings.HACKATHON_NAME)
                    # return back success to the check in app

        formatted_birthday = '{:02d}/{:02d}/{:04d}'.format(bday.month, bday.day, bday.year)
        return jsonify(name="{0} {1}".format(user.fname, user.lname), school=user.school_name, email=user.email,
                       age=calculate_age(bday), checked_in=user.checked_in,
                       status=user.status, birthday=formatted_birthday,
                       requires_eid=requires_eid)
    else:
        return jsonify(message='User does not exist'), 404
