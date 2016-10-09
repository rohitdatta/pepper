from pepper.app import DB
from flask import jsonify, request
from models import Announcement
from pepper import settings
from datetime import datetime

def announcement_list():
	announcements = Announcement.query().all()
	return jsonify(announcements)

def create_announcement():
	token = request.form.get('token')
	text = request.form.get('text')
	ts = datetime.fromtimestamp(float(request.form.get('timestamp')))
	if request.form.get('token') != settings.SLACK_TOKEN:
		return 'Unauthorized', 401
	send_notification = text.startswith('@channel')
	if send_notification:
		text = text[8:]
	announcement = Announcement(text, ts)
	DB.session.add(announcement)
	DB.session.commit()

	# Create a POST to Firebase
	return 'Created announcement'