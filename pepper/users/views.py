from flask import flash, g, jsonify, make_response, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from pytz import timezone
import redis
import requests
from sqlalchemy.exc import DataError, IntegrityError
from datetime import datetime
from urlparse import urlparse, urljoin

import batch
import helpers
from models import User
from pepper import settings, status
from pepper.app import DB
from pepper.legal.models import Waiver
from pepper.utils import calculate_age, get_current_user_roles, get_default_dashboard_for_role, \
    redirect_to_dashboard_if_authed, roles_required, s3, serializer, timed_serializer, user_status_blacklist, \
    user_status_whitelist, user_extra_application_required, is_safe_url


tz = timezone('US/Central')


@redirect_to_dashboard_if_authed
def landing():
    return render_template("static_pages/index.html")


@redirect_to_dashboard_if_authed
def sign_up():
    if not settings.REGISTRATION_OPENED:
        flash('Registration is not open yet, check back soon! :)', 'error')
        return redirect(url_for('landing'))
    if settings.REGISTRATION_CLOSED and not settings.PUZZLES_OPEN:
        flash('Registration has closed', 'error')
        return redirect(url_for('landing'))
    if request.method == 'GET':
        return render_template("users/sign_up.html", mlh_oauth_url=helpers.mlh_oauth_url)
    email = request.form.get('email')
    password = request.form.get('password')
    confirm_password = request.form.get('password-check')
    if not email or not password or not confirm_password:
        flash('Please fill out the required fields!', 'error')
        return redirect(request.url)
    if password != confirm_password:
        flash("The given passwords don't match!", 'error')
        return redirect(request.url)
    user = User.query.filter_by(email=email).first()
    if user is not None:
        flash('An account with this email has already been made! Please log in.', 'error')
        return redirect(url_for('login'))
    user_info = {
        'type': 'local',
        'email': email,
        'password': password,
    }
    user = User(user_info)
    DB.session.add(user)
    DB.session.commit()
    g.log = g.log.bind(email=email)
    g.log.info('Successfully created user from sign-up flow')

    login_user(user, remember=True)
    flash(
        'You have created your {0} account. We sent you a verification email. You need to verify your email before we can accept you to {0}'.format(
            settings.HACKATHON_NAME), 'success')
    return redirect(url_for('complete-registration'))


@redirect_to_dashboard_if_authed
def callback():
    url = 'https://my.mlh.io/oauth/token'
    body = {
        'client_id': settings.MLH_APPLICATION_ID,
        'client_secret': settings.MLH_SECRET,
        'code': request.args.get('code'),
        'grant_type': 'authorization_code',
        'redirect_uri': settings.BASE_URL + "callback"
    }
    resp = requests.post(url, params=body)
    try:
        json = resp.json()
    except Exception as e:
        g.log = g.log.bind(error=e, response=resp)
        g.log.error('Error Decoding JSON')
        flash('MyMLH had an error, please sign up here.', 'error')
        return redirect(url_for('sign-up'))

    if resp.status_code == 401:  # MLH sent expired token
        redirect_url = helpers.mlh_oauth_url

        g.log = g.log.bind(auth_code=request.args.get('code'), http_status=resp.status_code, resp=resp.text,
                           redirect_url=redirect_url, request_url=resp.url)
        g.log.error('Got expired auth code, redirecting: ')
        flash('MyMLH had an error, please sign up here.', 'error')
        return redirect(url_for('sign-up'))

    if 'access_token' in json:
        access_token = json['access_token']
    else:  # This is VERY bad, we should never hit this error
        g.log = g.log.bind(auth_code=request.args.get('code'), http_status=resp.status_code, resp=resp.text, body=body)
        g.log.error('URGENT: FAILED BOTH MLH AUTH CODE CHECKS')
        flash('MyMLH had an error, please sign up here.', 'error')
        return redirect(url_for('sign-up'))

    user = User.query.filter_by(access_token=access_token).first()
    if user is None:  # create the user
        try:
            user_info = helpers.get_mlh_user_data(access_token)
            user_info['type'] = 'MLH'
            user_info['access_token'] = access_token
            g.log = g.log.bind(email=user_info['data']['email'])
            user = User.query.filter_by(email=user_info['data']['email']).first()
            if user is None:
                if settings.REGISTRATION_CLOSED and not settings.PUZZLES_OPEN:
                    flash('Registration has closed', 'error')
                    return redirect(url_for('login'))
                if settings.REGISTRATION_OPENED:
                    g.log.info('Creating a new user from MLH info')
                    user = User(user_info)
                else:
                    flash('Registration is currently closed', 'error')
                    return redirect(url_for('landing'))
            else:
                user.access_token = access_token
                g.log = g.log.bind(email=user_info['data']['email'])
                g.log.info('added mlh access token for user')
            DB.session.add(user)
            DB.session.commit()
            login_user(user, remember=True)
            if user.confirmed:
                return redirect(url_for('dashboard'))
            elif user.type == 'local':
                # user didn't confirm email but signed up locally
                return redirect(url_for('complete-registration'))

            # don't send another email if they come back way later to add an mlh login
            batch.send_confirmation_email(user)
            flash(
                'You have created your {0} account. We sent you a verification email. You need to verify your email before we can accept you to {0}'.format(
                    settings.HACKATHON_NAME), 'success')
            g.log.info('Successfully created user')
            return redirect(url_for('complete-mlh-registration'))
        except IntegrityError:
            # a unique value already exists this should never happen
            DB.session.rollback()
            flash('A fatal error occurred. Please contact us for help', 'error')
            return redirect(url_for('landing'))
        except Exception as e:
            g.log.error('{}: {}'.format(type(e), e))
            g.log.error('Unable to create the user')
            flash('A fatal error occurred. Please contact us for help', 'error')
            return redirect(url_for('landing'))
    login_user(user, remember=True)
    return redirect(url_for('dashboard'))


@login_required
@user_status_whitelist(status.NEW)
def complete_mlh_registration():
    if current_user.type == 'local':
        # local sign up users should go to the other form
        return redirect(url_for('complete-registration'))
    if request.method == 'GET':
        return render_template("users/complete_mlh_registration.html", required=True, user=current_user)

    if request.form.get('mlh') != 'TRUE':
        flash('You must agree to the MLH Code of Conduct', 'error')
        return redirect(request.url)
    user_info = extract_mlh_info()
    if 'error' in user_info:
        flash(user_info['error'], 'error')
        return redirect(request.url)
    user_info.update(extract_resume(current_user.fname, current_user.lname, resume_required=True))
    if 'error' in user_info:
        flash(user_info['error'], 'error')
        return redirect(request.url)
    helpers.update_user_info(current_user, user_info)

    return complete_user_sign_up()


def extract_mlh_info():
    num_hackathons = request.form.get('num_hackathons')
    try:
        if int(num_hackathons) > 9223372036854775807:
            return {'error': "{} seems like a lot of hackathons! I don't think you've been to that many".format(
                num_hackathons)}
    except ValueError:
        return {'error': 'Please enter a number in number of hackathons'}
    race_list = request.form.getlist('race')
    if not race_list:
        return {'error': 'You must fill out the required fields:\nWhat race(s) do you identify with?'}
    race = 'NO_DISCLOSURE' if 'NO_DISCLOSURE' in race_list else ','.join(race_list)
    user_info = {
        'skill_level': request.form.get('skill_level'),
        'num_hackathons': num_hackathons,
        'race': race,
        'class_standing': request.form.get('class_standing'),
        'needs_travel_reimbursement': request.form.get('travel_reimbursement') == 'TRUE',
        'campus_ambassador': request.form.get('campus_ambassador') == 'TRUE',
    }
    if user_info['needs_travel_reimbursement']:
        user_info['why_travel_reimbursement'] = request.form.get('why_travel_reimbursement')
    if user_info['campus_ambassador']:
        user_info.update({
            'facebook_account': request.form.get('facebook_account'),
            'campus_ambassadors_application': request.form.get('campus_ambassadors_application'),
        })
    if None in user_info.values():
        missing_fields = (helpers.display_field_name(key) for key, value in user_info.iteritems() if value is None)
        message = 'You must fill out the required fields:\n' + 's, '.join(missing_fields)
        return {'error': message}
    workshops = request.form.get('workshops')
    if workshops:
        user_info['workshops'] = workshops
    return user_info


def extract_resume(first_name, last_name, resume_required=True):
    resume = request.files.get('resume')
    g.log.info(current_user.hashid)
    if resume:
        if helpers.is_pdf(resume.filename):  # if pdf upload to AWS
            # TODO: get rid of DEBUG path
            if settings.DEBUG:
                g.log.info("Uploading resume...")
            else:
                s3.Object(settings.S3_BUCKET_NAME,
                          u'resumes/{0}, {1} ({2}).pdf'.format(last_name, first_name,
                                                               current_user.hashid)).put(Body=resume)
        else:
            # resume was uploaded but wrong file format
            return {'error': 'Resume must be in PDF format'}
    elif resume_required:
        return {'error': 'Please upload your resume'}
    return {}


def complete_user_sign_up():
    if settings.REGISTRATION_CLOSED:
        current_user.status = status.LATE
    else:
        current_user.status = status.WAITLISTED if settings.SENT_ACCEPTANCES else status.PENDING
    current_user.time_applied = datetime.utcnow()
    batch.keen_add_event(current_user.id, 'sign_ups', current_user.time_applied)
    try:
        DB.session.add(current_user)
        DB.session.commit()
    except DataError as e:
        flash('There was an error with your registration information. Please try again.', 'error')
        return redirect(request.url)
    g.log = g.log.bind(email=current_user.email)
    g.log.info('User successfully applied')

    if current_user.confirmed:
        batch.send_applied_email(current_user)
        flash(
            'Congratulations! You have successfully applied for {0}! You should receive a confirmation email shortly'.format(
                settings.HACKATHON_NAME), 'success')
        return redirect(url_for('dashboard'))
    elif current_user.type == 'local':
        # we couldn't send these emails to people who signed up locally
        # until now since we didn't have their first names
        batch.send_confirmation_email(current_user)
    flash(
        'Congratulations! You have successfully applied for {0}! You must confirm your email before your application will be considered!'.format(
            settings.HACKATHON_NAME), 'success')
    return redirect(url_for('dashboard'))


@login_required
@user_status_whitelist(status.NEW)
def complete_registration():
    if current_user.type == 'MLH':
        # mlh users should complete the MLH registration form
        return redirect(url_for('complete-mlh-registration'))
    if request.method == 'GET':
        return render_template('users/edit_information.html', required=True, user=current_user)

    if request.form.get('mlh') != 'TRUE':
        flash('You must agree to the MLH Code of Conduct', 'error')
        return redirect(request.url)
    user_info = extract_user_info(resume_required=True)
    if 'error' in user_info:
        flash(user_info['error'], 'error')
        return redirect(request.url)

    helpers.update_user_info(current_user, user_info)

    return complete_user_sign_up()


def extract_user_info(resume_required=False):
    user_info = {
        'type': 'local',
        'fname': request.form.get('first_name'),
        'lname': request.form.get('last_name'),
        'birthday': request.form.get('date_of_birth'),
        'major': request.form.get('major'),
        'shirt_size': request.form.get('shirt_size'),
        'dietary_restrictions': request.form.get('dietary_restrictions'),
        'gender': request.form.get('gender'),
        'phone_number': request.form.get('phone_number'),
        'special_needs': request.form.get('special_needs', '').strip(),
        'school_name': request.form.get('school_name'),
    }

    if request.form.get('gender_other') != '' and user_info['gender'] == 'Other':
        user_info['gender'] = request.form.get('gender_other')

    if None in user_info.values():
        missing_fields = (helpers.display_field_name(key) for key, value in user_info.iteritems() if value is None)
        message = 'You must fill out the required fields:\n' + ', '.join(missing_fields)
        return {'error': message}

    user_info.update(extract_mlh_info())
    if 'error' in user_info:
        return user_info
    user_info.update(extract_resume(user_info['fname'], user_info['lname'], resume_required=resume_required))
    return user_info


@login_required
def dashboard():
    if current_user.status == status.NEW:
        if current_user.type == 'local':
            return redirect(url_for('complete-registration'))
        return redirect(url_for('complete-mlh-registration'))
    if current_user.status == status.PENDING or current_user.status == status.LATE:
        return render_template('users/dashboard/pending.html', user=current_user)
    elif current_user.status == status.ACCEPTED:
        return redirect(url_for('accept-invite'))
    elif current_user.status == status.SIGNING:
        return redirect(url_for('sign'))
    elif current_user.status == status.CONFIRMED:
        return render_template('users/dashboard/confirmed.html', user=current_user)
    elif current_user.status == status.DECLINED:
        return render_template('users/dashboard/declined.html', user=current_user)
    elif current_user.status == status.REJECTED:
        return render_template('users/dashboard/rejected.html', user=current_user)
    elif current_user.status == status.WAITLISTED:
        return render_template('users/dashboard/waitlisted.html', user=current_user)
    if 'corp' in get_current_user_roles():
        return redirect(url_for('corp-dash'))
    return render_template('users/dashboard/dashboard.html', user=current_user)


@login_required
def accept():
    if current_user.status not in [status.ACCEPTED, status.ADMIN]:  # they aren't allowed to accept their invitation
        message = {
            status.NEW: "You haven't completed your application for {0}! "
                        "Please submit your application before visiting this page!"
                .format(settings.HACKATHON_NAME),
            status.PENDING: "You haven't been accepted to {0}! "
                            "Please wait for your invitation before visiting this page!"
                .format(settings.HACKATHON_NAME),
            status.CONFIRMED: "You've already accepted your invitation to {0}! "
                              "We look forward to seeing you here!"
                .format(settings.HACKATHON_NAME),
            status.REJECTED: "You've already rejected your {0} invitation. "
                             "Unfortunately, for space considerations "
                             "you cannot change your response."
                .format(settings.HACKATHON_NAME),
            None: "Corporate users cannot view this page."
        }
        if current_user.status in message:
            flash(message[current_user.status], 'error')
        return redirect(url_for('dashboard'))
    if request.method == 'GET':
        return render_template('users/accept.html', user=current_user)
    else:
        if 'accept' in request.form:  # User has accepted the invite
            current_user.status = status.SIGNING
            flash('You have successfully confirmed your invitation to {0}'.format(settings.HACKATHON_NAME))
        else:
            current_user.status = status.DECLINED
        DB.session.add(current_user)
        DB.session.commit()
        user_decision = status.CONFIRMED if current_user.status == status.SIGNING else status.DECLINED
        batch.keen_add_event(current_user.id, user_decision, datetime.utcnow())
        return redirect(url_for('dashboard'))


def extract_waiver_info(user):
    signed_info = {}
    for key in (
            'relative_name', 'relative_email', 'relative_num', 'allergies', 'medications', 'special_health_needs',
            'medical_signature', 'medical_date', 'indemnification_signature',
            'indemnification_date', 'photo_signature', 'photo_date', 'ut_eid'):
        signed_info[key] = request.form.get(key)
    required_fields = ['relative_name', 'relative_email', 'relative_num', 'medical_signature',
                       'medical_date', 'indemnification_signature', 'indemnification_date',
                       'photo_signature', 'photo_date']
    if None in [signed_info[key] for key in required_fields]:
        return {'error': 'Must fill all required fields'}
    if user.school_id == 23:
        if signed_info['ut_eid'] == None:
            return {'error': 'Must fill out UT EID'}

    date_fmt = '%B %d, %Y'
    for key in ('medical_date', 'indemnification_date', 'photo_date'):
        signed_info[key] = datetime.strptime(signed_info[key], date_fmt)
    signed_info['user_id'] = user.id
    return signed_info

@login_required
def sign():
    if current_user.status not in [status.ADMIN, status.SIGNING]:  # they aren't allowed to accept their invitation
        message = {
            status.NEW: "You haven't completed your application for {0}! Please submit your application before visiting this page!".format(
                settings.HACKATHON_NAME),
            status.PENDING: "You haven't been accepted to {0}! Please wait for your invitation before visiting this page!".format(
                settings.HACKATHON_NAME),
            status.CONFIRMED: "You've already accepted your invitation to {0}! We look forward to seeing you here!".format(
                settings.HACKATHON_NAME),
            status.REJECTED: "You've already rejected your {0} invitation. Unfortunately, for space considerations you cannot change your response.".format(
                settings.HACKATHON_NAME),
            None: "Corporate users cannot view this page."
        }
        if current_user.status in message:
            flash(message[current_user.status], 'error')
        return redirect(url_for('dashboard'))
    if request.method == 'GET':
        date_fmt = '%B %d, %Y'
        today = datetime.now(tz).date()
        return render_template('users/sign.html', user=current_user, date=today.strftime(date_fmt))
    else:
        signed_info = extract_waiver_info(current_user)
        if 'error' in signed_info:
            flash(signed_info['error'], 'error')
            return redirect(request.url)
        waiver = Waiver(signed_info)
        DB.session.add(waiver)
        DB.session.commit()

        current_user.status = status.CONFIRMED
        DB.session.add(current_user)
        DB.session.commit()

        batch.keen_add_event(current_user.id, 'waivers_signed', waiver.time_signed)

        batch.send_attending_email(current_user)

        flash("You've successfully confirmed your invitation to {}".format(settings.HACKATHON_NAME), 'success')
        return redirect(url_for('dashboard'))


@login_required
@user_extra_application_required
@user_status_whitelist(status.CONFIRMED)
def additional_status():
    if request.method == 'GET':
        if current_user.campus_ambassador and current_user.is_campus_ambassador is not None:
            if current_user.is_campus_ambassador:
                campus_ambassador_status = True
            else:
                campus_ambassador_status = False
        else:
            campus_ambassador_status = None

        if current_user.needs_travel_reimbursement and current_user.has_travel_reimbursement is not None:
            if current_user.has_travel_reimbursement:
                travel_reimbursement_status = True
            else:
                travel_reimbursement_status = False
        else:
            travel_reimbursement_status = None

        return render_template('users/additional_status.html', campus_ambassador_status=campus_ambassador_status,
                               travel_reimbursement_status=travel_reimbursement_status, user=current_user)


@login_required
@user_status_whitelist(status.CONFIRMED)
def accept_reimbursement():
    if not current_user.has_travel_reimbursement:
        flash('You are not authorized to do this action', 'error')
        return redirect(url_for('dashboard'))
    if current_user.accepted_travel_reimbursement:
        flash('You have already accepted your travel reimbursement!', 'warning')
    else:
        g.log.info('Accepted travel reimbursement')
        current_user.accepted_travel_reimbursement = True
        DB.session.add(current_user)
        DB.session.commit()
    return redirect(url_for('additional-status'))

@redirect_to_dashboard_if_authed
def login():
    if request.method == 'GET':
        return render_template('users/login.html', mlh_oauth_url=helpers.mlh_oauth_url)
    # handle login POST logic
    email = request.form.get('email')
    password = request.form.get('password')
    if not email or not password:
        flash('Please fill out the required fields!', 'error')
        return redirect(request.url)
    user = User.query.filter_by(email=email).first()
    if user is None:
        flash("We couldn't find an account related with this email. Please verify the email entered.", 'warning')
        return redirect(request.url)
    elif not user.password:  # they signed up with MLH or are a corporate account and have no password
        flash('An error occurred. Please contact us for more information.', 'error')
        return redirect(request.url)
    elif not helpers.check_password(user.password, password):
        flash('Invalid password. Please try again.', 'warning')
        return redirect(request.url)
    login_user(user, remember=True)
    target = request.args.get('next')
    if (target and is_safe_url(target)):
        return redirect(target)
    else:
        flash('Logged in successfully!', 'success')
        return redirect(url_for(get_default_dashboard_for_role()))


def logout():
    logout_user()
    return redirect(url_for('landing'))


@login_required
@user_status_blacklist(status.NEW)
def edit_profile():
    if request.method == 'POST':
        user_info = extract_user_info(resume_required=False)
        if 'error' in user_info:
            flash(user_info['error'], 'error')
            return redirect(request.url)

        helpers.update_user_info(current_user, user_info, commit=True)
        flash('Successfully updated profile!', 'success')

    return render_template('users/edit_information.html', required=False, user=current_user)


def forgot_password():
    if request.method == 'GET':
        return render_template('users/forgot_password.html')
    else:
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            batch.send_forgot_password_email(user)
        flash('If there is a registered user with {}, then a password reset email has been sent!'.format(email),
              'success')
        return redirect(url_for('login'))


def reset_password(token):
    try:
        email = timed_serializer.loads(token, salt=settings.RECOVER_SALT, max_age=86400)
        user = User.query.filter_by(email=email).first()
    except Exception as e:
        g.log.error('error: {}'.format(e))
        return render_template('layouts/error.html', error="That's an invalid link"), 401

    if request.method == 'GET':
        # find the correct user and log them in then prompt them for new password
        return render_template('users/reset_password.html')
    else:
        # take the password they've submitted and change it accordingly
        password = request.form.get('password')
        password_check = request.form.get('password-check')
        if not password or not password_check:
            flash('Please fill out all required fields!', 'error')
            return redirect(request.url)
        if user:
            if request.form.get('password') == request.form.get('password-check'):
                user.password = helpers.hash_pwd(request.form['password'])
                DB.session.add(user)
                DB.session.commit()
                login_user(user, remember=True)
                flash('Succesfully changed password!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('You need to enter the same password in both fields!', 'error')
                return redirect(url_for('reset-password'), token=token)
        else:
            flash('Failed to reset password. This is an invalid link. Please contact us if this error persists',
                  'error')
            return redirect(url_for('forgot-password'))


@login_required
@user_status_whitelist(status.NEW, status.PENDING)
def resend_confirmation():
    email = request.values.get('email')
    if not email:
        return jsonify({
            'message': 'Invalid request',
            'category': 'error',
        })
    if email != current_user.email:
        return jsonify({
            'message': 'You are not allowed to do that',
            'category': 'error',
        })
    if current_user.confirmed:
        return jsonify({
            'message': 'Your email is already confirmed',
            'category': 'warning',
        })
    batch.send_confirmation_email(current_user)
    return jsonify({
        'message': "We sent another confirmation email to you! If you don't see it in a few minutes, check your spam or contact us",
        'category': 'success',
    })


def confirm_account(token):
    try:
        email = serializer.loads(token)
        user = User.query.filter_by(email=email).first()
        if user is None:
            flash('Invalid link', 'error')
            return redirect(url_for('landing'))
        if current_user.is_authenticated:
            if current_user.email != email:
                flash('This link is not for you!', 'error')
                return redirect(url_for(get_default_dashboard_for_role()))
            if current_user.confirmed:
                flash('You are already confirmed', 'success')
                return redirect(url_for(get_default_dashboard_for_role()))
        if user.confirmed:
            flash('This user is already confirmed', 'error')
            return redirect(url_for('login'))
        user.confirmed = True
        DB.session.add(user)
        DB.session.commit()
        if user.status == status.PENDING:
            batch.send_applied_email(user)
            if settings.SENT_ACCEPTANCES:
                user.status = status.WAITLISTED
                DB.session.add(user)
                DB.session.commit()
        flash('Successfully confirmed account', 'success')
        return redirect(url_for('complete-registration'))
    except:
        return render_template('layouts/error.html',
                               message="That's an invalid link. Please contact {} for help.".format(
                                   settings.GENERAL_INFO_EMAIL)), 401


@login_required
@user_status_whitelist('CONFIRMED')
def view_campus_ambassadors():
    ambassadors = User.query.filter_by(is_campus_ambassador=True, status='CONFIRMED').order_by(User.school_name).all()
    return render_template('users/view_campus_ambassadors.html', ambassadors=ambassadors)

"""
@login_required
def dashboard():
    if current_user.type == 'corporate':
        return redirect(url_for('corp-dash'))
    if current_user.type == 'admin':
        return redirect(url_for('admin-dash'))

    if current_user.status == status.NEW:
        update_user_data('MLH')
        return redirect(url_for('confirm-registration'))
    elif current_user.status == status.ACCEPTED:
        return redirect(url_for('accept-invite'))
    elif current_user.status == status.SIGNING:
        return redirect(url_for('sign'))
    elif current_user.status == status.CONFIRMED:
        return render_template('users/dashboard/confirmed.html', user=current_user)
    elif current_user.status == status.DECLINED:
        return render_template('users/dashboard/declined.html', user=current_user)
    elif current_user.status == status.REJECTED:
        return render_template('users/dashboard/rejected.html', user=current_user)
    elif current_user.status == status.WAITLISTED:
        return render_template('users/dashboard/waitlisted.html', user=current_user)
    elif current_user.status == status.ADMIN:
        users = User.query.order_by(User.created.asc())
        return render_template('users/dashboard/admin_dashboard.html', user=current_user, users=users)
    return render_template('users/dashboard/pending.html', user=current_user)


#  Refresh the MyMLH profile info
@login_required
def refresh_from_mlh():
    user_info = helpers.get_mlh_user_data(current_user.access_token)
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


# Editing of the attendee profile info after applying
@login_required
def edit_resume():
    if current_user.status == status.NEW:
        return redirect(url_for('dashboard'))
    if request.method == 'GET':
        # render template for editing resume
        return render_template('users/dashboard/update_resume.html', user=current_user)
    else:
        # Update your resume
        if 'resume' in request.files:
            resume = request.files['resume']
            if helpers.is_pdf(resume.filename):  # if pdf upload to AWS
                s3.Object(settings.S3_BUCKET_NAME,
                          'resumes/{0}, {1} ({2}).pdf'.format(current_user.lname, current_user.fname,
                                                              current_user.hashid)).put(Body=resume)
            else:
                flash('Resume must be in PDF format', 'error')
                return redirect(request.url)
        else:
            flash('Please upload your resume', 'error')
            return redirect(request.url)
        flash('You successfully updated your resume', 'success')
        return redirect(request.url)


# allow attendee to view their own resume
@login_required
def view_own_resume():
    data_object = s3.Object(settings.S3_BUCKET_NAME, u'resumes/{0}, {1} ({2}).pdf'
                            .format(current_user.lname, current_user.fname,
                                    current_user.hashid)).get()
    response = make_response(data_object['Body'].read())
    response.headers['Content-Type'] = 'application/pdf'
    return response


@login_required
def accept():
    if current_user.status != 'ACCEPTED':  # they aren't allowed to accept their invitation
        message = {
            status.NEW: "You haven't completed your application for {0}! "
                        "Please submit your application before visiting this page!"
                .format(settings.HACKATHON_NAME),
            status.PENDING: "You haven't been accepted to {0}! "
                            "Please wait for your invitation before visiting this page!"
                .format(settings.HACKATHON_NAME),
            status.CONFIRMED: "You've already accepted your invitation to {0}! "
                              "We look forward to seeing you here!"
                .format(settings.HACKATHON_NAME),
            status.REJECTED: "You've already rejected your {0} invitation. "
                             "Unfortunately, for space considerations "
                             "you cannot change your response."
                .format(settings.HACKATHON_NAME),
            None: "Corporate users cannot view this page."
        }
        if current_user.status in message:
            flash(message[current_user.status], 'error')
        return redirect(url_for('dashboard'))
    if request.method == 'GET':
        return render_template('users/accept.html', user=current_user)
    else:
        if 'accept' in request.form:  # User has accepted the invite
            current_user.status = status.SIGNING
            flash('You have successfully confirmed your invitation to {0}'.format(settings.HACKATHON_NAME))
        else:
            current_user.status = status.DECLINED
        DB.session.add(current_user)
        DB.session.commit()
        user_decision = status.CONFIRMED if current_user.status == status.SIGNING else status.DECLINED
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

"""
