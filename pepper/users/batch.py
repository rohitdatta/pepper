from models import User
from pepper import settings
from pepper.app import DB, worker_queue
from pepper.utils import send_email, serializer, timed_serializer

from flask import render_template, render_template_string, url_for, g
from sqlalchemy import or_
import keen
import random


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
        email_contexts = []
        for user in users:
            html = render_template('emails/generic_message.html', content=msg_body)
            html = render_template_string(html, user=user)
            email_contexts.append((user.email, html))
        for i in range(0, len(email_contexts), settings.MAX_BATCH_EMAILS):
            worker_queue.enqueue(_send_batch_emails_with_context, subject,
                                 email_contexts[i:i+settings.MAX_BATCH_EMAILS])
    else:
        emails = [user.email for user in users]
        html = render_template('emails/generic_message.html', content=msg_body)
        html = render_template_string(html)
        for i in range(0, len(emails), settings.MAX_BATCH_EMAILS):
            worker_queue.enqueue(_send_static_batch_emails, subject, html, emails[i:i+settings.MAX_BATCH_EMAILS])


def _send_batch_emails_with_context(subject, email_contexts):
    for email, html_content in email_contexts:
        send_email(settings.GENERAL_INFO_EMAIL, subject, email, html_content=html_content)


def _send_static_batch_emails(subject, html_content, emails):
    for email in emails:
        send_email(settings.GENERAL_INFO_EMAIL, subject, email, html_content=html_content)


def accept_fifo(num_to_accept, include_waitlist):
    if include_waitlist:
        potential_attendees = User.query.filter(or_(User.status == 'WAITLISTED', User.status == 'PENDING'))
    else:
        potential_attendees = User.query.filter_by(status='PENDING')
    ordered_attendees = potential_attendees.order_by(User.time_applied.asc()).limit(
        num_to_accept).all()

    for attendee in ordered_attendees:
        if attendee.status == 'WAITLISTED':
            html = render_template('emails/application_decisions/accept_from_waitlist.html', user=attendee)
        else:  # User should be in pending state, but catch all just in case
            html = render_template('emails/application_decisions/accepted.html', user=attendee)
        attendee.status = 'ACCEPTED'
        DB.session.commit()
        send_email(settings.GENERAL_INFO_EMAIL, "Congrats! {} Invitation"
                   .format(settings.HACKATHON_NAME),
                   attendee.email, html_content=html)


def random_accept(num_to_accept, include_waitlist):
    if include_waitlist:
        pool = User.query.filter(or_(User.status == 'PENDING', User.status == 'WAITLISTED')).all()
    else:
        pool = User.query.filter_by(status='PENDING').all()

    accepted = random.sample(set(pool), num_to_accept)
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


def keen_add_event(user_id, event_type, count):
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
