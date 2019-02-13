# The purpose of this script is to move all of the pending users with confirmed emails to the waitlist

from flask import render_template
from flask_script import Command

from pepper.users.models import User
from pepper.app import DB
from pepper.utils import send_email
from pepper import status, settings

class SendRecruitmentEmailCommand(Command):
    def run(self):
        users = []

        query_result = User.query.filter(
            User.school_name.op('~')('[uU][nN][iI].*'),
            User.school_name.op('~')('.*[tT][eE][xX][aA][sS].*'),
            User.school_name.op('~')('.*[aA][uU][sS].*')
        ).all()
        users += query_result

        query_result = User.query.filter(
            User.school_name.op('~')('.*[uU][tT] [aA][uU].*')
        ).all()
        users += query_result

        for user in users:
            user_email = user.email

            html = render_template('emails/application_decisions/freetail_recruitment.html', user=user)
            send_email(
                settings.GENERAL_INFO_EMAIL,
                "Join Freetail Hackers -- the organizers of {}!".format(settings.HACKATHON_NAME),
                user.email,
                html_content=html,
                attachments=None
            )
            print ('Sent freetail recruitment email to user_id={}'.format(user.id))
