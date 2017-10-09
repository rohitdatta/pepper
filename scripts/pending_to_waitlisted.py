# The purpose of this script is to move all of the pending users with confirmed emails to the waitlist

from flask import render_template
from flask_script import Command
from sqlalchemy import and_

from pepper.users.models import User
from pepper.app import DB
from pepper.utils import send_email
from pepper import status, settings


class PendingToWaitlistedCommand(Command):
    def run(self):
        users = User.query.filter(and_(User.status == status.PENDING, User.confirmed.is_(True))).all()
        for user in users:
            user.status = status.WAITLISTED
            html = render_template('emails/application_decisions/waitlisted.html', user=user)
            DB.session.add(user)
            DB.session.commit()
            send_email(settings.GENERAL_INFO_EMAIL, "Your {} Application Status".format(settings.HACKATHON_NAME),
                       user.email, html_content=html)
            print 'Moving user_id={} to the waitlist'.format(user.id)
