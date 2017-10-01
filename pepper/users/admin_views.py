import random

import helpers
from models import User, UserRole
from views import logout_user
from pepper import settings
from pepper.app import DB
from pepper.utils import calculate_age, roles_required, send_email

from flask import flash, g, redirect, render_template, render_template_string, request, url_for
from flask.ext.login import current_user, login_required
import keen
from sqlalchemy import and_, or_


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
            login_user(user, remember=True)
            return redirect(url_for('admin-dash'))
    else:
        return 'Cannot create new admin'


@login_required
@roles_required('admin')
def admin_dashboard():
    return render_template('users/admin/dashboard.html')


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
                     'email': request.form['email'].lower(),
                     'type': 'corporate'}
        user = User(user_data)
        DB.session.add(user)
        DB.session.commit()
        g.log = g.log.bind(corp_user='{0} {1} <{2}>'.format(user_data['fname'], user_data['lname'], user_data['email']))
        g.log = g.log.bind(admin='{0} {1} <{2}>'.format(current_user.fname, current_user.lname, current_user.email))
        g.log.info('Created new corporate account')
        try:
            helpers.send_recruiter_invite(user)
            flash('Successfully invited {0} {1}'.format(user_data['fname'], user_data['lname']), 'success')
        except Exception:
            flash('Unable to send recruiter invite', 'error')
        return render_template('users/admin/create_user.html')


# Developers can use this portal to log into any particular user when debugging
@login_required
@roles_required('admin')
def debug_user():
    if request.method == 'GET':
        return render_template('users/admin/internal_login.html')
    else:
        id = request.form['id']
        user = User.query.filter_by(id=id).first()
        if user is None:
            return 'User does not exist'
        logout_user()
        login_user(user, remember=True)
        return redirect(url_for('landing'))


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
            accepted_attendees = User.query.filter_by(status='WAITLISTED').order_by(User.time_applied.asc()).limit(
                num_to_accept).all()
            for attendee in accepted_attendees:
                attendee.status = 'ACCEPTED'
                DB.session.commit()
                html = render_template('emails/application_decisions/accept_from_waitlist.html', user=attendee)
                send_email(settings.GENERAL_INFO_EMAIL, "You're In! {} Invitation".format(settings.HACKATHON_NAME),
                           attendee.email, html_content=html)
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
                send_email(settings.GENERAL_INFO_EMAIL, "You're In! {} Invitation".format(settings.HACKATHON_NAME),
                           attendee.email, html_content=html)

            # set everyone else to go from pending to waitlisted
            pending_attendees = User.query.filter_by(status='PENDING').all()
            for pending_attendee in pending_attendees:
                pending_attendee.status = 'WAITLISTED'
                html = render_template('emails/application_decisions/waitlisted.html', user=pending_attendee)
                DB.session.commit()
                send_email(settings.GENERAL_INFO_EMAIL, "You're {} Application Status".format(settings.HACKATHON_NAME),
                           pending_attendee.email, html_content=html)
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


@login_required
@roles_required('admin')
def set_mlh_id():
    if request.method == 'GET':
        return render_template('users/admin/set_mlh_id.html')
    else:
        mlh_users = User.query.filter_by(type='MLH')
        i = 0
        for user in mlh_users:
            if user.access_token is not None:
                user_info = helpers.get_mlh_user_data(user.access_token)
                if 'data' in user_info:
                    user.mlh_id = user_info['data']['id']
                    DB.session.add(user)
                    DB.session.commit()
            i += 1
            print i

        return 'Finished updating ids'


@login_required
@roles_required('admin')
def resend_recruiter_invite():
    # TODO Get the recruiter email
    email = 'test@dhs2014.com'
    user = User.query.filter_by(email=email).first()
    try:
        helpers.send_recruiter_invite(user)
        return jsonify()
    except Exception as e:
        g.log = g.log.bind(error=e)
        g.log.error('Unable to resend recruiter email: ')
        return jsonify(), 501
