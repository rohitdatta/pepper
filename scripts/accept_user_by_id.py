from flask import render_template
from flask_script import Command, Option
from pepper.utils import serializer

from pepper.users.models import User
from pepper.app import DB
from pepper.utils import send_email
from pepper import status, settings

class AcceptUserByID(Command):

    option_list = (
        Option('--user_id', dest='user_id'),
    )

    def run(self, user_id):
        user = User.query.filter(User.id==user_id).first()
        if user is None:
            print 'There is no user with user_id={}'.format(user_id)
        else:
            user.status = status.ACCEPTED
            html = render_template('emails/application_decisions/accepted.html', user=user)
            DB.session.add(user)
            DB.session.commit()
            send_email(settings.GENERAL_INFO_EMAIL, "Your {} Application Status".format(settings.EVENT_NAME),
                       user.email, html_content=html)
            print 'Accepting user_id={}'.format(user.id)

