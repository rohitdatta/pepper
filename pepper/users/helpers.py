import functools
import time
import urllib2
from urlparse import urlparse, urljoin

from flask import render_template, url_for, redirect, request, g
import requests
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash

from pepper import settings
from pepper import utils
from pepper.app import DB

mlh_oauth_url = ('https://my.mlh.io/oauth/authorize?'
                 'client_id={0}&'
                 'redirect_uri={1}callback&'
                 'response_type=code&'
                 'scope=email+phone_number+demographics+birthday+education+event').format(
    settings.MLH_APPLICATION_ID, urllib2.quote(settings.BASE_URL, ':/'))


def hash_pwd(password):
    return generate_password_hash(password)


def check_password(hashed, password):
    return check_password_hash(hashed, password)


def send_recruiter_invite(user):
    g.log.info('Sending a recruiter invite for user {}'.format(user.id))
    # send invite to the recruiter
    token = utils.serializer.dumps(user.email)
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


def get_mlh_user_data(access_token):
    return requests.get('https://my.mlh.io/api/v2/user.json', params={'access_token': access_token}).json()


def update_user_info(user, user_info, commit=False):
    for key, value in user_info.items():
        setattr(user, key, value)
    if commit:
        DB.session.add(user)
        DB.session.commit()


# Check if a filename is a pdf
def is_pdf(filename):
    return '.' in filename and filename.lower().rsplit('.', 1)[1] == 'pdf'


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc


def display_field_name(field_name):
    if field_name == 'fname':
        return 'First Name'
    if field_name == 'lname':
        return 'Last Name'
    return field_name.replace('_', ' ').title()


def sleep():
    time.sleep(5)
