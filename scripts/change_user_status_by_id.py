from flask import render_template
from flask_script import Command, Option
from pepper.utils import serializer

from pepper.users.models import User
from pepper.app import DB
from pepper.utils import send_email
from pepper import status, settings

class ChangeUserStatusByID(Command):

    option_list = (
        Option('--new_status', dest='new_status'),
        Option('--user_id', dest='user_id'),
        
    )

    def run(self, user_id, new_status):
        if user_id is None or new_status is None:
            print "Please specify user_id and new_status"
            return

        user = User.query.filter(User.id==user_id).first()
        if user is None:
            print 'There is no user with user_id={}'.format(user_id)
        else:
            new_status = new_status.lower()
            changed_status = False
            if (new_status == 'accepted'):
                user.status = status.ACCEPTED
                html = render_template('emails/application_decisions/accepted.html', user=user)
                changed_status = True
            elif (new_status == 'waitlisted'):
                user.status = status.WAITLISTED
                html = render_template('emails/application_decisions/waitlisted.html', user=user)
                changed_status = True
            elif (new_status == 'rejected'):
                user.status = status.REJECTED
                html = render_template('emails/application_decisions/rejected.html', user=user)
                changed_status = True
            else:
                print '{} is not a valid status'.format(new_status)
            if (changed_status):            
                DB.session.add(user)
                DB.session.commit()
                send_email(settings.GENERAL_INFO_EMAIL, "Your {} Application Status".format(settings.EVENT_NAME), user.email, html_content=html)
                print '{} user_id={}'.format(new_status, user.id)

