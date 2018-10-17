# The purpose of this script is to move all of the pending users with confirmed emails to the waitlist

from flask import render_template
from flask_script import Command
from sqlalchemy import and_

from pepper.users.models import User
from pepper.app import DB
from pepper.utils import send_email
from pepper import status, settings

import base64
import qrcode

class SendPreeventEmailCommand(Command):
    def run(self):
        users = User.query.filter(and_(User.status == status.CONFIRMED, User.confirmed.is_(True))).all()
        for user in users:
            user_email = user.email
            qr_code = qrcode.make(user_email)
            encoded = base64.b64encode(qrcode).decode()
            attachments = [{'encoded': encoded, 'file_type': 'image/png', 'filename': 'qrcode.png'}]
            html = render_template('emails/application_decisions/preevent.html', user=user)
            send_email(settings.GENERAL_INFO_EMAIL, "Your {} Application Status".format(settings.HACKATHON_NAME),
                       user.email, html_content=html, attachments=attachments)
            print ('Sent event day email to user_id={}'.format(user.id))
