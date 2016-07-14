
from nucleus.app import DB
from datetime import datetime

class User(DB.Model):
	__tablename__ = 'users'

	id = DB.Column(DB.Integer, primary_key=True)
	email = DB.Column(DB.String(128))
	fname = DB.Column(DB.String(128))
	lname = DB.Column(DB.String(128))
	status = DB.Column(DB.String(255))
	created = DB.Column(DB.DateTime)
	class_standing = DB.Column(DB.String(255))
	major = DB.Column(DB.String(255))
	shirt_size = DB.Column(DB.String(255))
	dietary_restrictions = DB.Column(DB.String(255))
	birthday = DB.Column(DB.Date)
	gender = DB.Column(DB.String(255))
	phone_number = DB.Column(DB.String(255))
	school = DB.Column(DB.String(255)) # TODO: get this to be a school obj
	special_needs = DB.Column(DB.Text)
	checked_in = DB.Column(DB.Boolean)
	# roles = DB.relationship('Role', secondary='user_roles', backref=DB.backref('users', lazy='dynamic'))
	access_token = DB.Column(DB.String(255))

	def __init__(self, dict):
		self.email = dict['data']['email']
		self.fname = dict['data']['first_name']
		self.lname = dict['data']['last_name']
		self.status = 'NEW'
		self.created = datetime.utcnow()
		self.major = dict['data']['major']
		self.shirt_size = dict['data']['shirt_size']
		self.dietary_restrictions = dict['data']['dietary_restrictions']
		self.birthday = dict['data']['date_of_birth']
		self.gender = dict['data']['gender']
		self.phone_number = dict['data']['phone_number']
		self.special_needs = dict['data']['special_needs']
		self.checked_in = False

	@property
	def is_authenticated(self):
		return True

	@property
	def is_active(self):
		return True

	@property
	def is_anonymous(self):
		return False

	def get_id(self):
		return unicode(self.id)