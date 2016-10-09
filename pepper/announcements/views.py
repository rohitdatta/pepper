from pepper.app import DB
from flask import jsonify
from models import Announcement

def announcement_list():
	announcements = Announcement.query().all()
	return jsonify(announcements)

def create_announcement():
	announcement = Announcement() #TODO: look at post data

	# Create a POST to Firebase
	return 'Created announcement'