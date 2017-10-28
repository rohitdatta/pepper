from collections import defaultdict
from datetime import datetime

from flask import flash, g, redirect, render_template, request, url_for, jsonify
from flask_login import current_user, login_required, login_user
import keen
from pytz import timezone
import redis
from rq.job import Job
from sqlalchemy import and_, or_

import batch
import helpers
from models import User, UserRole
from views import extract_waiver_info, logout_user
from pepper import settings, status
from pepper.app import DB, worker_queue
from pepper.legal import Waiver
from pepper.utils import calculate_age, roles_required, send_email


tz = timezone('US/Central')


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
            user.status = status.ADMIN
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
        unverified_users = User.query.filter(and_(User.type == 'corporate',
                                                  User.password is None)).all()
        return render_template('users/admin/create_corporate_user.html', unverified=unverified_users)
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
        return render_template('users/admin/create_corporate_user.html')


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
        users = User.query.filter(User.status == status.WAITLISTED).order_by(
            User.time_applied.asc()).all()
        return render_template('users/admin/accept_users.html', users=users)
    elif request.method == 'POST':
        g.log.info('Starting batch acceptance')
        acceptance_heuristic = request.form.get('acceptance_heuristic')
        num_acceptance = int(request.form.get('num_acceptance'))

        if num_acceptance <= 0:
            flash('Invalid number for acceptance. Please try again.', 'error')
            return redirect(url_for('batch-modify'))
        else:
            if acceptance_heuristic == 'fifo':  # First in, first out
                batch.accept_fifo(num_acceptance)
            else:  # Randomly select num_acceptance users
                batch.accept_random(num_acceptance)
            flash('Successfully modified user statuses. However, this will take a while.'
                  ' Please refresh this page later to see the changes.', 'info')
            g.log.info('Batch acceptances have been queued')
            return redirect(url_for('batch-modify'))


@login_required
@roles_required('admin')
def send_email_to_users():
    if request.method == 'GET':
        all_users = User.query.all()
        return render_template('users/admin/send_email.html', users=all_users)

    if not request.form.get('content'):
        flash('Please enter a message')
        return redirect(url_for('send-email'))
    if not request.form.get('subject'):
        flash('Please enter a subject')
        return redirect(url_for('send-email'))

    targeted_users = []
    user_id_set = set()

    from_name = request.form.get('from_name')

    statuses = request.form.getlist('status')
    status_users = User.query.filter(or_(User.status.in_(statuses))).all() if statuses else []
    checkbox_user_ids = [int(current_user_id) for current_user_id in request.form.getlist('user_ids')]
    checkbox_users = User.query.filter(or_(User.id.in_(checkbox_user_ids))).all() if checkbox_user_ids else []

    for user in status_users:
        if user.id not in user_id_set:
            user_id_set.add(user.id)
            targeted_users.append(user)

    for user in checkbox_users:
        if user.id not in user_id_set:
            user_id_set.add(user.id)
            targeted_users.append(user)

    if len(targeted_users) > 0:
        batch.send_batch_email(request.form.get('content'), request.form.get('subject'),
                               targeted_users, request.form.get('user-context') == 'TRUE',
                               from_name=from_name)

    flash('Batch email(s) successfully sent', 'success')
    return redirect(url_for('send-email'))


@login_required
@roles_required('admin')
def job_view(job_key):
    job = Job.fetch(job_key, connection=redis.from_url(settings.REDIS_URL))
    if job.is_finished:
        return 'Finished'
    else:
        return 'Nope'


@login_required
@roles_required('admin')
def reject_users():
    waitlisted_users = User.query.filter(User.status == status.WAITLISTED).all()

    if request.method == 'GET':
        return render_template('users/admin/reject_users.html', users=waitlisted_users)
    else:
        for user in waitlisted_users:
            html = render_template('emails/application_decisions/rejected.html', user=user)
            send_email(settings.GENERAL_INFO_EMAIL, "Update from HackTX", user.email, html_content=html)
            user.status = status.REJECTED
            DB.session.add(user)
            DB.session.commit()
        flash('Successfully rejected all waitlisted user(s)', 'success')
        return redirect(url_for('reject-users'))


def get_valid_teams():
    users = User.query.filter(
        and_(or_(User.status == status.WAITLISTED,
                 User.status == status.ACCEPTED,
                 User.status == status.SIGNING,
                 User.status == status.CONFIRMED),
             User.team_id.isnot(None),
             User.time_team_join.isnot(None),
             User.confirmed.is_(True))).order_by(User.time_team_join).all()

    team_structure_dict = defaultdict(list)
    sorted_users = []

    # Getting team count as well as grouping users by team_id
    for u in users:
        team_structure_dict[u.team_id].append(u)

    # Removing teams that only have 1 member or have already been accepted
    for team_id, members in team_structure_dict.items():
        if len(members) <= 1 or all(member.status != status.WAITLISTED for member in members):
            team_structure_dict.pop(team_id, None)

    # Sorting the teams by the 2nd member's time_team_join
    sorted_teams = sorted(team_structure_dict.items(), key=lambda (k, v): v[1].time_team_join)

    # Inserting the teams into list
    for team_id, members in sorted_teams:
        sorted_users += [teammate for teammate in team_structure_dict[team_id] if teammate.status == 'WAITLISTED']

    return sorted_users


@login_required
@roles_required('admin')
def accept_teams():
    if request.method == 'GET':
        return render_template('users/admin/modify_users.html', users=get_valid_teams())

    selected_user_ids = [int(user_id) for user_id in request.form.getlist('user_ids')]
    selected_users = User.query.filter(or_(User.id.in_(selected_user_ids))).all()

    for user in selected_users:
        previous_status = user.status
        user.status = status.ACCEPTED
        g.log.info('Modifying user_id={} previous_status={} current_status={}'.format(user.id,
                                                                                      previous_status,
                                                                                      user.status))

    for user in selected_users:
        DB.session.add(user)
    DB.session.commit()
    batch.send_accepted_emails(selected_users)

    flash(
        'Successfully accepted selected users. However, this will take a while.'
        ' Please refresh this page later to see the remaining pending user(s).',
        'info')
    return redirect(url_for('accept-teams'))


@login_required
@roles_required('admin')
def check_in_manual():
    if request.method == 'GET':
        return render_template('users/admin/check_in.html')
    else:
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()

        def error(mesg):
            flash(mesg, 'error')
            return redirect(request.url)

        if user is None:
            return error('User not found')

        age = calculate_age(user.birthday)
        if age < 18:
            return error('User under 18')
        if user.status not in [status.CONFIRMED, status.SIGNING]:
            return error('User not confirmed')
        if user.checked_in:
            return error('User is already checked in')
        if user.status == status.SIGNING:
            return redirect(url_for('check-in-sign', user_id=user.id))
        requires_eid = user.school_id == 23 and not Waiver.query.filter_by(user_id=user.id).first().ut_eid
        return render_template('users/admin/confirm_check_in.html', user=user, age=age,
                               requires_eid=requires_eid)


@login_required
@roles_required('admin')
def check_in_sign(user_id):
    user = User.query.filter_by(id=user_id).first()
    if user is None:
        flash('User does not exist', 'error')
        return redirect(url_for('manual-check-in'))
    if request.method == 'GET':
        date_fmt = '%B %d, %Y'
        today = datetime.now(tz).date()
        return render_template('users/sign.html', user=user, date=today.strftime(date_fmt),
                               check_in=True)

    signed_info = extract_waiver_info(user)
    if 'error' in signed_info:
        flash(signed_info['error'], 'error')
        return redirect(request.url)
    waiver = Waiver(signed_info)
    DB.session.add(waiver)
    DB.session.commit()

    user.status = status.CONFIRMED
    DB.session.add(user)
    DB.session.commit()

    batch.keen_add_event(user.id, 'waivers_signed', waiver.time_signed)
    flash("You've successfully confirmed your invitation to {}".format(settings.HACKATHON_NAME), 'success')

    age = calculate_age(user.birthday)
    return render_template('users/admin/confirm_check_in.html', user=user, age=age,
                           requires_eid=False)


@login_required
@roles_required('admin')
def check_in_post():
    email = request.form.get('email')
    user = User.query.filter_by(email=email).first()
    if user.school_id == 23:
        waiver = Waiver.query.filter_by(user_id=user.id).first()
        if not waiver.ut_eid:
            eid = request.form.get('eid')
            waiver.ut_eid = eid
            DB.session.add(waiver)
            DB.session.commit()
    user.checked_in = True
    DB.session.add(user)
    DB.session.commit()
    batch.keen_add_event(user.id, 'check_in', datetime.utcnow())
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
