
from mito.app import DB
from datetime import datetime
from helpers import hash_pwd
from flask_user import UserMixin
from mito.utils import resume_hash


class User(DB.Model, UserMixin):
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
	roles = DB.relationship('Role', secondary='user_roles', backref=DB.backref('users', lazy='dynamic'))
	access_token = DB.Column(DB.String(255))
	password = DB.Column(DB.String(100))
	type = DB.Column(DB.String(100))
	# race = DB.Column(DB.String(255))

	def __init__(self, dict):
		if dict['type'] == 'MLH': # if creating a MyMLH user
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
			self.type = 'MLH'
			self.access_token = dict['access_token']
		elif dict['type'] == 'corporate': # creating a corporate user
			email = dict['email'].lower().strip()
			# email_validation = validate_email(email) #TODO: Email validation
			# if not email_validation['is_valid']:
			# 	if email_validation['did_you_mean']:
			# 		raise ValueError('%s is an invalid address. Perhaps you meant %s' % (email, email_validation['did_you_mean']))
			# 	else:
			# 		raise ValueError('%s is an invalid address' % email)

			self.email = email
			self.password = hash_pwd(dict['password'])
			self.fname = dict['fname']
			self.lname = dict['lname']
			self.type = 'corporate'

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

	@property
	def hashid(self):
		try:
			return self._hashid
		except AttributeError:
			if not self.id:
				raise Exception("this form doesn't have an id yet, commit it first.")
			self._hashid = resume_hash.encode(self.id)
		return self._hashid

	@classmethod
	def get_with_hashid(cls, hashid):
		try:
			id = resume_hash.decode(hashid)[0]
			return cls.query.get(id)
		except IndexError:
			return None

class Role(DB.Model):
	__tablename__ = 'role'
	id = DB.Column(DB.Integer(), primary_key=True)
	name = DB.Column(DB.String(), unique=True)

class UserRoles(DB.Model):
	__tablename__ = 'user_roles'
	id = DB.Column(DB.Integer(), primary_key=True)
	user_id = DB.Column(DB.Integer(), DB.ForeignKey('users.id', ondelete='CASCADE'))
	role_id = DB.Column(DB.Integer(), DB.ForeignKey('role.id', ondelete='CASCADE'))
