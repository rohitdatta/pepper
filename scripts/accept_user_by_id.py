from flask import render_template
from flask_script import Command, Option
from pepper.utils import serializer

from pepper.users.models import User
from pepper.app import DB
from pepper.utils import send_email
from pepper import status, settings

class AcceptUserByID(Command):

    option_list = (
        Option('--new_status', dest='new_status')
        Option('--user_id', dest='user_id'),
        
    )

    def run(self, user_id, new_status):
        user = User.query.filter(User.id==user_id).first()
        if user is None:
            print 'There is no user with user_id={}'.format(user.id)
        else:
            new_status = new_status.lower()
            if (new_status == 'accept'):
                user.status = status.ACCEPTED
                html = render_template('emails/application_decisions/accepted.html', user=user)
            DB.session.add(user)
            DB.session.commit()
            # send_email(settings.GENERAL_INFO_EMAIL, "Your {} Application Status".format(settings.HACKATHON_NAME),
                    #    user.email, html_content=html)
            print 'Accepting user_id={}'.format(user.id)

