from collections import defaultdict
import batch
import helpers
from models import User, UserRole
from views import logout_user
from pepper import settings
from pepper.app import DB, worker_queue
from pepper.utils import calculate_age, roles_required, send_email

from flask import flash, g, redirect, render_template, request, url_for, jsonify
from flask.ext.login import current_user, login_required, login_user
import keen
import redis
from rq.job import Job
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
    users = User.query.filter(
        and_(or_(User.status == 'PENDING', User.status == 'WAITLISTED'), User.confirmed.is_(True))).order_by(
        User.time_applied.asc()).all()
    if request.method == 'GET':
        return render_template('users/admin/accept_users.html', users=users)
    elif request.method == 'POST':
        g.log.info('Starting batch acceptance')
        acceptance_heuristic = request.form.get('acceptance_heuristic')
        num_acceptance = int(request.form.get('num_acceptance'))
        include_waitlisted = request.form.get('include_waitlisted', True) == 'true'

        if num_acceptance <= 0:
            flash('Invalid number for acceptance. Please try again.', 'error')
            return redirect(url_for('batch-modify'))
        else:
            if acceptance_heuristic == 'fifo':  # First in, first out
                worker_queue.enqueue(batch.accept_fifo, num_acceptance, include_waitlisted)
            else:  # Randomly select num_acceptance users
                worker_queue.enqueue(batch.accept_random, num_acceptance, include_waitlisted)
            flash('Successfully modified user statuses. However, this will take a while.'
                  ' Please refresh this page later to see the changes.', 'info')
            g.log.info('Batch acceptances have been queued')
            return redirect(url_for('batch-modify'))


@login_required
@roles_required('admin')
def send_email_to_users():
    all_users = User.query.all()
    if request.method == 'GET':
        return render_template('users/admin/send_email.html', users=all_users)
    else:
        targeted_users = []
        user_id_set = set()

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
                                   targeted_users, request.form.get('user-context') == 'TRUE')

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
    waitlisted_users = User.query.filter(User.status == 'WAITLISTED').all()

    if request.method == 'GET':
        return render_template('users/admin/reject_users.html', users=waitlisted_users)
    else:
        for user in waitlisted_users:
            html = render_template('emails/application_decisions/rejected.html', user=user)
            send_email(settings.GENERAL_INFO_EMAIL, "Update from HackTX", user.email, html_content=html)
            user.status = 'REJECTED'
            DB.session.add(user)
            DB.session.commit()
        flash('Successfully rejected all waitlisted user(s)', 'success')
        return redirect(url_for('reject-users'))


@login_required
@roles_required('admin')
def get_pending_team_users():
    users = User.query.filter(
        and_(User.status == 'PENDING',
             User.team_id.isnot(None),
             User.time_team_join.isnot(None),
             User.confirmed.is_(True))).all()

    team_size_dict = defaultdict(int)
    team_structure_dict = defaultdict(list)
    teams_sort_criteria = []
    sorted_users = []

    # Getting team count as well as grouping users by team_id
    for u in users:
        team_size_dict[u.team_id] += 1
        team_structure_dict[u.team_id].append(u)

    # Removing teams that only have 1 member
    for team_id in team_structure_dict.keys():
        if team_size_dict[team_id] <= 1:
            team_structure_dict.pop(team_id, None)

    # Getting the sorting criteria by extracting the 2nd member's time_team_join
    for team_id in team_structure_dict.keys():
        team_users = sorted(team_structure_dict[team_id], key=lambda k: k.time_team_join)
        team_structure_dict[team_id] = team_users
        teams_sort_criteria.append((team_users[1].time_team_join, team_id))

    # Sorting the teams by the 2nd member's time_team_join
    teams_sort_criteria = sorted(teams_sort_criteria, key=lambda k: k[0])

    # Inserting the teams into list
    for (timestamp, team_id) in teams_sort_criteria:
        sorted_users += team_structure_dict[team_id]

    return sorted_users


@login_required
@roles_required('admin')
def modify_users():
    if request.method == 'GET':
        return render_template('users/admin/modify_users.html', users=get_pending_team_users())
    elif request.method == 'POST':
        selected_user_ids = [int(user_id) for user_id in request.form.getlist('user_ids')]
        selected_users = User.query.filter(or_(User.id.in_(selected_user_ids))).all()

        for user in selected_users:
            previous_status = user.status
            user.status = 'ACCEPTED'
            DB.session.add(user)
            DB.session.commit()
            g.log.info('Modifying user_id={} previous_status={} current_status={}'.format(user.id,
                                                                                          previous_status,
                                                                                          user.status))
            batch.send_accepted_email(user)

        flash(
            'Successfully accepted selected users. However, this will take a while.'
            ' Please refresh this page later to see the remaining pending user(s).',
            'info')
        return render_template('users/admin/modify_users.html', users=get_pending_team_users())


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


@login_required
@roles_required('admin')
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
