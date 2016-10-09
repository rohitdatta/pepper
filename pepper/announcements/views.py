from pepper.app import DB
from flask import jsonify, request
from models import Announcement
from pepper import settings
from datetime import datetime
import requests

def announcement_list():
	announcements = Announcement.query().all()
	return jsonify(announcements)

def create_announcement():
	token = request.form.get('token')
	text = request.form.get('text')
	ts = datetime.fromtimestamp(float(request.form.get('timestamp')))
	if request.form.get('token') != settings.SLACK_TOKEN:
		return 'Unauthorized', 401
	send_notification = text.startswith('<!channel>')
	if send_notification:
		text = text[10:]
	announcement = Announcement(text, ts)
	DB.session.add(announcement)
	DB.session.commit()

	if send_notification:
		resp = requests.post('https://fcm.googleapis.com/fcm/send', headers={
			'Authorization': 'key={}'.format(settings.FIREBASE_KEY)
		}, data={
			'to': "/topics/announcement",
			'time_to_live': 0,
			'data': {
				'title': 'HackTX',
				'text': text,
				'vibrate': True
			}
		})
		print resp.status_code
	# Create a POST to Firebase
	return 'Created announcement'