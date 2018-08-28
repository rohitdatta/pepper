import random

from flask import render_template, render_template_string, url_for, g
import keen

from models import User
from pepper import settings, status
from pepper.app import DB, worker_queue
from pepper.utils import send_email, serializer, timed_serializer


def send_accepted_emails(users):

    def generate_html(user):
        return render_template('emails/application_decisions/round2.html', user=user)

    send_batch_emails_with_context(
        users, 'Your {} application decision'.format(settings.HACKATHON_NAME),
        generate_html)


def send_confirmation_email(user):
    token = serializer.dumps(user.email)
    url = url_for('confirm-account', token=token, _external=True)
    html = render_template('emails/confirm_account.html', link=url, user=user)
    worker_queue.enqueue(send_email, settings.GENERAL_INFO_EMAIL, 'Confirm Your Account', user.email, None, html)


def send_applied_email(user):
    html = render_template('emails/applied.html', user=user)
    worker_queue.enqueue(send_email, settings.GENERAL_INFO_EMAIL, 'Thank you for applying to {0}'
                         .format(settings.HACKATHON_NAME), user.email,
                         None, html)


def send_forgot_password_email(user):
    token = timed_serializer.dumps(user.email, salt=settings.RECOVER_SALT)
    url = url_for('reset-password', token=token, _external=True)
    html = render_template('emails/reset_password.html', user=user, link=url)
    txt = render_template('emails/reset_password.txt', user=user, link=url)
    g.log.info('Sending password reset to:', email=user.email)
    worker_queue.enqueue(send_email, settings.GENERAL_INFO_EMAIL, 'Your password reset link', user.email, txt, html)


def send_attending_email(user):
    # send email saying that they are confirmed to attend
    html = render_template('emails/application_decisions/confirmed_invite.html', user=user)
    worker_queue.enqueue(send_email, settings.GENERAL_INFO_EMAIL,
                         "You're confirmed for {}".format(settings.HACKATHON_NAME),
                         user.email, None, html)


def send_batch_email(content, subject, users, needs_user_context, from_name=None):
    g.log.info('Sending batch emails to {} users'.format(len(users)))
    lines = content.split('\r\n')
    msg_body = u""
    for line in lines:
        msg_body += u'<tr><td class="content-block">{}</td></tr>\n'.format(line)
    if needs_user_context:
        def generate_html(user):
            html = render_template('emails/generic_message.html', content=msg_body)
            return render_template_string(html, user=user)

        send_batch_emails_with_context(users, subject, generate_html, from_name=from_name)
    else:
        html = render_template('emails/generic_message.html', content=msg_body)
        html = render_template_string(html)
        send_batch_static_emails(users, subject, html, from_name=from_name)


def send_batch_emails_with_context(users, subject, html_func, from_name=None):
    for i in range(0, len(users), settings.MAX_BATCH_EMAILS):
        email_contexts = [(user.email, html_func(user)) for user in users[i: i + settings.MAX_BATCH_EMAILS]]
        worker_queue.enqueue(_send_batch_emails_with_context, subject, email_contexts, from_name)


def _send_batch_emails_with_context(subject, email_contexts, from_name=None):
    for email, html_content in email_contexts:
        send_email(settings.GENERAL_INFO_EMAIL, subject, email, html_content=html_content, from_name=from_name)


def send_batch_static_emails(users, subject, html_content, from_name=None):
    for i in range(0, len(users), settings.MAX_BATCH_EMAILS):
        emails = [user.email for user in users[i: i + settings.MAX_BATCH_EMAILS]]
        worker_queue.enqueue(_send_batch_static_emails, emails, subject, html_content, from_name)


def _send_batch_static_emails(emails, subject, html_content, from_name=None):
    for email in emails:
        send_email(settings.GENERAL_INFO_EMAIL, subject, email, html_content=html_content, from_name=from_name)



def _filter_individuals(users):
    import admin_views
    team_ids = set(user.id for user in admin_views.get_valid_teams())
    return [user for user in users if user.id not in team_ids]


def accept_fifo(num_to_accept):
    potential_users = User.query.filter(User.status == status.WAITLISTED).order_by(
        User.time_applied.asc()).all()
    accept_users(_filter_individuals(potential_users)[:num_to_accept])

    def generate_html(user):
        return render_template('emails/application_decisions/round2.html', user=user)

    send_batch_emails_with_context(
        potential_users, "Your {} application decision".format(settings.HACKATHON_NAME),
        generate_html)


def accept_random(num_to_accept):
    potential_users = User.query.filter(User.status == status.WAITLISTED).all()

    # get individuals
    filtered_users = _filter_individuals(potential_users)

    accept_users(random.sample(set(filtered_users), num_to_accept))

    def generate_html(user):
        return render_template('emails/application_decisions/round2.html', user=user)

    send_batch_emails_with_context(
        potential_users, "Your {} application decision".format(settings.HACKATHON_NAME),
        generate_html)


def accept_users(accepted_users):
    former_user_statuses = {}
    for user in accepted_users:
        former_user_statuses[user.id] = user.status
        user.status = status.ACCEPTED
        DB.session.add(user)
    DB.session.commit()


def _keen_add_event(event_type, data, count):
    try:
        keen.add_event(event_type, data)
        print 'success'
    except Exception as e:
        print e
        if count < settings.KEEN_MAX_RETRIES:
            worker_queue.enqueue(_keen_add_event, event_type, data, count + 1)
        else:
            print 'Keen failed too many times, {}'.format(event_type)


def keen_add_event(user_id, event_type, event_time):
    user = User.query.filter_by(id=user_id).first()
    fmt = '%Y-%m-%dT%H:%M:%S.%f'
    data = {
        'date_of_birth': user.birthday,
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
            'timestamp': event_time.strftime(fmt)
            },
        'interests': user.interests,
        'skill_level': user.skill_level,
        'races': user.race,
        'num_hackathons': user.num_hackathons,
        'class_standing': user.class_standing,
        'shirt_size': user.shirt_size,
        'special_needs': user.special_needs
    }
    worker_queue.enqueue(_keen_add_event, event_type, data, 0)
