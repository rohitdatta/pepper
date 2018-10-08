from flask import render_template
from flask_script import Command, Option
from pepper.utils import serializer

from pepper.users.models import User
from pepper.app import DB
from pepper.utils import send_email
from pepper import status, settings

class ChangeUserStatusByID(Command):

    option_list = (
        Option('--current_status', dest='current_status', required=True),
        Option('--new_status', dest='new_status', required=True),
        Option('--user_id', dest='user_id', required=True),
    )

    def run(self, user_id, new_status, current_status):
        if user_id is None or new_status is None:
            print('Please specify user_id and new_status')
            return

        user = User.query.filter(User.id==user_id).first()
        if user is None:
            print('There is no user with user_id={}'.format(user_id))
            return

        if current_status is not None:
            assert user.status.lower() == current_status.lower(), 'User status is {}'.format(user.status)

        new_status = new_status.lower()
        changed_status = False
        if (new_status == 'accepted'):
            user.status = status.ACCEPTED
            html = render_template('emails/application_decisions/accepted.html', user=user)
            changed_status = True
        elif (new_status == 'waitlisted'):
            user.status = status.WAITLISTED
            html = render_template('emails/application_decisions/waitlisted-initial.html', user=user)
            changed_status = True
        elif (new_status == 'rejected'):
            user.status = status.REJECTED
            html = render_template('emails/application_decisions/rejected.html', user=user)
            changed_status = True
        else:
            print('{} is not a valid status'.format(new_status))
        if (changed_status):
            DB.session.add(user)
            DB.session.commit()
            send_email(settings.GENERAL_INFO_EMAIL, 'Your {} Application Status'.format(settings.EVENT_NAME), user.email, html_content=html)
            print('{} user_id={}'.format(new_status, user.id))