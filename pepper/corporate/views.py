from flask import request, render_template, flash, redirect, url_for, g, make_response
from flask.ext.login import login_user, current_user
from pepper.users import User
from helpers import check_password
from pepper.utils import corp_login_required, roles_required, s3, serializer, timed_serializer, send_email
from pepper import settings
from sqlalchemy import distinct, and_
from pepper.app import DB
from pepper.users.helpers import hash_pwd
from pepper.users.models import UserRole
import time


def login():
    if request.method == 'GET':
        if current_user.is_authenticated:
            return redirect(url_for('corp-dash'))
        return render_template('corporate/login.html')
    else:
        email = request.form['email'].lower()
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user is None:
            flash("We couldn't find an account related with this email. Please verify the email entered.", "warning")
            return redirect(url_for('corp-login'))
        elif user.password is None:
            flash('This account has not been setup yet. Please click the login link in your setup email.')
            return redirect(url_for('corp-login'))
        elif not check_password(user.password, password):
            flash("Invalid Password. Please verify the password entered.", 'warning')
            return redirect(url_for('corp-login'))
        login_user(user, remember=True)
        flash('Logged in successfully!', 'success')
        if 'ADMIN' in user.roles:
            return redirect(url_for('admin-dash'))
        return redirect(url_for('corp-dash'))


def new_user_setup(token):
    try:
        email = serializer.loads(token)
        user = User.query.filter_by(email=email).first()
        if user.password is not None:
            flash('User has already been setup. If you need to change the password, please reset your password.',
                  'error')
            return redirect(url_for('corp-dash'))
    except:
        return render_template('layouts/error.html', title='Invalid Link', message="That's an invalid link"), 401

    if request.method == 'GET':
        return render_template('users/account_setup.html', user=user)
    else:
        if user:
            if request.form.get('password') == request.form.get('password-check'):
                user.password = hash_pwd(request.form['password'])
                DB.session.add(user)
                DB.session.commit()
                # add corp role to the user
                role = UserRole(user.id)
                role.name = 'corp'
                DB.session.add(role)
                DB.session.commit()

                login_user(user, remember=True)

                g.log = g.log.bind(
                    name='{0} {1} <{2}>'.format(current_user.fname, current_user.lname, current_user.email))
                g.log.info('Successfully set up account for ')
                flash('Successfully setup account!', 'success')
                return redirect(url_for('corp-dash'))
            else:
                flash('You need to enter the same password in both fields!', 'error')
                return redirect(url_for('new-user-setup', token=token))
        else:
            flash(
                'Failed to setup your account. Please double check the link in your email. If this problem persists, please reach out to us to investigate',
                'error')
            return redirect(url_for('landing'))


def forgot_password():
    if request.method == 'GET':
        return render_template('users/forgot_password.html')
    else:
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            token = timed_serializer.dumps(user.email, salt=settings.RECOVER_SALT)
            url = url_for('corp-reset-password', token=token, _external=True)
            html = render_template('emails/reset_password.html', user=user, link=url)
            txt = render_template('emails/reset_password.txt', user=user, link=url)
            send_email('hello@hacktx.com', 'Your password reset link', email, txt, html)
        flash('If there is a registered user with {}, then a password reset email has been sent!'.format(email),
              'success')
        return redirect(url_for('corp-login'))


def reset_password(token):
    try:
        email = timed_serializer.loads(token, salt=settings.RECOVER_SALT, max_age=86400)
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
                return redirect(url_for('corp-dash'))
            else:
                flash('You need to enter the same password in both fields!', 'error')
                return redirect(url_for('corp-reset-password', token=token))
        else:
            flash('Failed to reset password. This is an invalid link. Please contact us if this error persists',
                  'error')
            return redirect(url_for('corp-forgot-password'))


@corp_login_required
@roles_required('admin', 'corp')
def corporate_dash():
    return render_template('corporate/dashboard.html', user=current_user)


@corp_login_required
@roles_required('admin', 'corp')
def corporate_search():
    if request.method == 'GET':
        schools = DB.session.query(distinct(User.school_name)).all()
        majors = DB.session.query(distinct(User.major)).all()
        class_standings = DB.session.query(distinct(User.class_standing)).all()
        schools, majors, class_standings = [filter(lambda x: x[0] is not None, filter_list) for filter_list in
                                            [schools, majors, class_standings]]
        schools, majors, class_standings = [map(lambda x: x[0], filter_list) for filter_list in
                                            [schools, majors, class_standings]]
        schools.sort()
        majors.sort()
        class_standings.sort()
        return render_template('corporate/search.html', schools=schools, majors=majors, class_standings=class_standings)


@corp_login_required
@roles_required('admin', 'corp')
def search_results():
    start = time.time()
    schools = request.form.getlist('schools')
    class_standings = request.form.getlist('class_standings')
    majors = request.form.getlist('majors')
    attended = request.form.get('attended')
    users = User.query.filter(and_(User.status != 'NEW', User.type == 'MLH'))
    if schools:
        users = users.filter(User.school_name.in_(schools))
    if majors:
        users = users.filter(User.major.in_(majors))
    if class_standings:
        users = users.filter(User.class_standing.in_(class_standings))
    if attended:
        users = users.filter(User.checked_in)
    users = users.all()
    end = time.time()
    search_time = end - start
    g.log = g.log.bind(name='{0} {1} <{2}>'.format(current_user.fname, current_user.lname, current_user.email))
    g.log.info('Search made for schools:{0} , majors:{1}, class_standings:{2}, attended:{3} by'.format(schools, majors,
                                                                                                       class_standings,
                                                                                                       attended))
    return render_template('corporate/results.html', users=users, schools=schools, class_standings=class_standings,
                           majors=majors, time=search_time)


@corp_login_required
@roles_required('admin', 'corp')
def view_resume():
    hashid = request.args.get('id')
    user = User.get_with_hashid(hashid)
    g.log = g.log.bind(name='{0} {1} <{2}>'.format(current_user.fname, current_user.lname, current_user.email))
    g.log.info('Resume for {0} {1} <{2}> viewed by'.format(user.fname, user.lname, user.email))
    data_object = s3.Object(settings.S3_BUCKET_NAME,
                            u'resumes/{0}, {1} ({2}).pdf'.format(user.lname, user.fname, user.hashid)).get()
    User.get_with_hashid(hashid)
    response = make_response(data_object['Body'].read())
    response.headers['Content-Type'] = 'application/pdf'
    return response


@corp_login_required
@roles_required('admin', 'corp')
def download_all_resumes():
    return redirect(settings.RESUMES_LINK, code=200)
