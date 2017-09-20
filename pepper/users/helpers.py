import urllib2

from flask import render_template, url_for, flash, redirect
from flask.ext.login import current_user
import requests
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash

from pepper import settings
import pepper.utils

def hash_pwd(password):
    return generate_password_hash(password)


def check_password(hashed, password):
    return check_password_hash(hashed, password)


def send_status_change_notification(user):
    if user.status == 'ACCEPTED':
        # txt = render_template('')
        subject = "Congratulations! You've been accepted to {}".format(settings.HACKATHON_NAME)
    elif user.status == 'REJECTED':
        # txt =
        subject = "Your {} application decision".format(settings.HACKATHON_NAME)
    elif user.status == 'WAITLISTED':
        # txt =
        subject = "Update on your application to {}".format(settings.HACKATHON_NAME)

    # utils.send_email('hello@hacktx.com', subject, user.email, txt, html)


def send_recruiter_invite(user):
    # send invite to the recruiter
    token = utils.s.dumps(user.email)
    url = url_for('new-user-setup', token=token, _external=True)
    txt = render_template('emails/corporate_welcome.txt', user=user, setup_url=url)
    html = render_template('emails/corporate_welcome.html', user=user, setup_url=url)

    try:
        utils.send_email(from_email=settings.GENERAL_INFO_EMAIL,
                   subject='Your invitation to join my{}'.format(settings.HACKATHON_NAME),
                   to_email=user.email, txt_content=txt, html_content=html)
    except Exception as e:
        g.log = g.log.bind(error=e)
        g.log.error('Unable to send recruiter email: ')


def mlh_oauth_url():
    return ('https://my.mlh.io/oauth/authorize?'
            'client_id={0}&'
            'redirect_uri={1}callback&'
            'response_type=code&'
            'scope=email+phone_number+demographics+birthday+education+event').format(
                    settings.MLH_APPLICATION_ID, urllib2.quote(settings.BASE_URL))


def get_mlh_user_data(access_token):
    return requests.get('https://my.mlh.io/api/v2/user.json', params={'access_token': access_token}).json()


def get_default_dashboard_for_role():
    roles = utils.get_current_user_roles()
    if "admin" in roles:
        return "admin-dash"
    if "corp" in roles:
        return "corp-dash"
    return "dashboard"


def redirect_to_dashboard_if_authed():
    def wrapper(func):
        @functools.wraps(func)
        def decorated_view(*args, **kwargs):
            if current_user.is_authenticated:
                return redirect(url_for(get_default_dashboard_for_role()))
            return func(*args, **kwargs)
        return decorated_view
    return wrapper


def check_registration_opened():
    def wrapper(func):
        @functools.wraps(func)
        def decorated_view(*args, **kwargs):
            if settings.REGISTRATION_OPEN:
                return func(*args, **kwargs)
            return redirect(url_for('landing'))
        return decorated_view
    return wrapper
