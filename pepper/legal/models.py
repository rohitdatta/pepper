from datetime import datetime
from pepper.app import DB


class Waiver(DB.Model):
	__tablename__ = 'waivers'
	id = DB.Column(DB.Integer(), primary_key=True)
	user_id = DB.Column(DB.Integer(), DB.ForeignKey('users.id', ondelete='CASCADE'))
	relative_name = DB.Column(DB.String(128))
	relative_email = DB.Column(DB.String(128))
	relative_num = DB.Column(DB.String(32))

	allergies = DB.Column(DB.String(128))
	medications = DB.Column(DB.String(128))
	special_health_needs = DB.Column(DB.String(128))

	medical_signature = DB.Column(DB.String(64))
	medical_date = DB.Column(DB.Date)

	indemnification_signature = DB.Column(DB.String(64))
	indemnification_date = DB.Column(DB.Date)

	photo_signature = DB.Column(DB.String(64))
	photo_date = DB.Column(DB.Date)

	ut_eid = DB.Column(DB.String(32))

	time_signed = DB.Column(DB.DateTime)

	def __init__(self, dict):
		self.user_id = dict['user_id']
		self.relative_name = dict['relative_name']
		self.relative_email = dict['relative_email']
		self.relative_num = dict['relative_num']
		self.allergies = dict['allergies']
		self.medications = dict['medications']
		self.special_health_needs = dict['special_health_needs']
		self.medical_signature = dict['medical_signature']
		self.medical_date = dict['medical_date']
		self.indemnification_signature = dict['indemnification_signature']
		self.indemnification_date = dict['indemnification_date']
		self.photo_signature = dict['photo_signature']
		self.photo_date = dict['photo_date']
		self.ut_eid = dict['ut_eid']
		self.time_signed = datetime.utcnow()
