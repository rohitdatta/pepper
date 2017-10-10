import random

from flask import render_template, render_template_string, url_for, g
from sqlalchemy import and_, or_
import keen

from models import User
from pepper import settings, status
from pepper.app import DB, worker_queue
from pepper.utils import send_email, serializer, timed_serializer


def send_accepted_emails(users):
    def generate_html(user):
        return render_template('emails/application_decisions/accepted.html', user=user)
    send_batch_emails_with_context(users, 'Congrats! Your HackTX Invitation', generate_html)


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


def send_batch_email(content, subject, users, needs_user_context):
    g.log.info('Sending batch emails to {} users'.format(len(users)))
    lines = content.split('\r\n')
    msg_body = u""
    for line in lines:
        msg_body += u'<tr><td class="content-block">{}</td></tr>\n'.format(line)
    if needs_user_context:
        def generate_html(user):
            html = render_template('emails/generic_message.html', content=msg_body)
            return render_template_string(html, user=user)

        send_batch_emails_with_context(users, subject, generate_html)
    else:
        html = render_template('emails/generic_message.html', content=msg_body)
        html = render_template_string(html)
        send_batch_static_emails(users, subject, html)


def send_batch_emails_with_context(users, subject, html_func):
    for i in range(0, len(users), settings.MAX_BATCH_EMAILS):
        email_contexts = [(user.email, html_func(user)) for user in users[i: i + settings.MAX_BATCH_EMAILS]]
        worker_queue.enqueue(_send_batch_emails_with_context, subject, email_contexts)


def _send_batch_emails_with_context(subject, email_contexts):
    for email, html_content in email_contexts:
        send_email(settings.GENERAL_INFO_EMAIL, subject, email, html_content=html_content)


def send_batch_static_emails(users, subject, html_content):
    for i in range(0, len(users), settings.MAX_BATCH_EMAILS):
        emails = [user.email for user in users[i: i + settings.MAX_BATCH_EMAILS]]
        worker_queue.enqueue(_send_batch_static_emails, emails, subject, html_content)


def _send_batch_static_emails(emails, subject, html_content):
    for email in emails:
        send_email(settings.GENERAL_INFO_EMAIL, subject, email, html_content=html_content)



def _filter_individuals(users):
    filtered = []
    for user in users:
        if user.team is not None:
            num_team_eligible = sum(1 for u in user.team.users if u.confirmed)
            if num_team_eligible > 1:
                continue
        filtered.append(user)
    return filtered


def accept_fifo(num_to_accept, include_waitlisted):
    if include_waitlisted:
        potential_users = User.query.filter(
            and_(or_(User.status == status.WAITLISTED, User.status == status.PENDING), User.confirmed.is_(True)))
    else:
        potential_users = User.query.filter(and_(User.status == status.PENDING), User.confirmed.is_(True))

    potential_users = potential_users.order_by(User.time_applied.asc()).all()

    accept_users(_filter_individuals(potential_users))



def accept_random(num_to_accept, include_waitlisted):
    if include_waitlisted:
        filtered_users = User.query.filter(and_(or_(User.status == status.PENDING, User.status == status.WAITLISTED),
                                                User.confirmed.is_(True))).all()
    else:
        filtered_users = User.query.filter(and_(User.status == status.PENDING, User.confirmed.is_(True))).all()

    # get individuals
    filtered_users = _filter_individuals(filtered_users)

    accept_users(random.sample(set(filtered_users), num_to_accept))


def accept_users(accepted_users):
    former_user_statuses = {}
    for user in accepted_users:
        former_user_statuses[user.id] = user.status
        user.status = status.ACCEPTED
        DB.session.add(user)
        DB.session.commit()

    def generate_html(user):
        if former_user_statuses[user.id] == status.WAITLISTED:
            return render_template('emails/application_decisions/accept_from_waitlist.html',
                                   user=user)
        # User should be in pending state, but catch all just in case
        return render_template('emails/application_decisions/accepted.html', user=user)

    send_batch_emails_with_context(accepted_users,
                                  "You're In! {} Invitation".format(settings.HACKATHON_NAME),
                                   generate_html)


def keen_add_event(user_id, event_type, count, event_time):
    user = User.query.filter_by(id=user_id).first()
    fmt = '%Y-%m-%dT%H:%M:%S.%f'
    try:
        keen.add_event(event_type, {
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
                'timestamp': event_time.strftime(fmt)
            },
            'interests': user.interests,
            'skill_level': user.skill_level,
            'races': user.race,
            'num_hackathons': user.num_hackathons,
            'class_standing': user.class_standing,
            'shirt_size': user.shirt_size,
            'special_needs': user.special_needs
        })
        print 'success'
    except Exception as e:
        print e
        if count < 3:
            worker_queue.enqueue(keen_add_event, user_id, event_type, count + 1)
        else:
            print 'Keen failed too many times, {}'.format(event_type)
            # else:
            #     #user decision
            #     keen.add_event(event_type, {
            #         'date_of_birth': user.birthday.strftime(fmt),
            #         'dietary_restrictions': user.dietary_restrictions,
            #         'email': user.email,
            #         'first_name': user.fname,
            #         'last_name': user.lname,
            #         'gender': user.gender,
            #         'id': user.id,
            #         'major': user.major,
            #         'phone_number': user.phone_number,
            #         'school': {
            #             'id': user.school_id,
            #             'name': user.school_name
            #         },
            #         'skill_level': user.skill_level,
            #         'races': user.race.split(','),
            #         'num_hackathons': user.num_hackathons,
            #         'class_standing': user.class_standing,
            #         'shirt_size': user.shirt_size,
            #         'special_needs': current_user.special_needs
            #     })
