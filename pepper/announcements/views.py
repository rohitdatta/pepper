from pepper.app import DB, csrf
from flask import request, Response
from models import Announcement
from pepper import settings
from datetime import datetime
import requests
import json
from pytz import timezone

cst = timezone('US/Central')


def announcement_list():
    announcements = Announcement.query.all()
    announcement_list = []
    datetime_fmt = '%Y-%m-%d %H:%M:%S'
    for announcement in announcements:
        announcement_list.append({'text': announcement.text,
                                  'ts': datetime.strftime(announcement.timestamp, datetime_fmt)})
    return Response(json.dumps(announcement_list), mimetype='application/json')


@csrf.exempt
def create_announcement():
    token = request.form.get('token')
    text = request.form.get('text')
    ts = datetime.fromtimestamp(float(request.form.get('timestamp')))
    from_tz = timezone('UTC')
    ts = from_tz.localize(ts).astimezone(cst)
    if request.form.get('token') != settings.SLACK_TOKEN:
        return 'Unauthorized', 401
    send_notification = text.startswith('<!channel>')
    if send_notification:
        text = text[text.find(' ') + 1:]
    announcement = Announcement(text, ts)
    DB.session.add(announcement)
    DB.session.commit()

    if send_notification:
        resp = requests.post('https://fcm.googleapis.com/fcm/send', headers={
            "Authorization": "key={}".format(settings.FIREBASE_KEY)
        }, json={
            "to": "/topics/announcements",
            "time_to_live": 0,
            "data": {
                "title": "HackTX",
                "text": text,
                "vibrate": "true"
            }
        })

        # Send iOS notification
        resp = requests.post('https://fcm.googleapis.com/fcm/send', headers={
            "Authorization": "key={}".format(settings.FIREBASE_KEY)
        }, json={
            "to": "/topics/ios",
            "priority": "high",
            "notification": {
                "title": "New Announcement!",
                "body": text
            }
        })
    # print resp.status_code

    # Create a POST to Firebase
    return 'Created announcement'
