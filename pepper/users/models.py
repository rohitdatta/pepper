from pepper.app import DB
from datetime import datetime
from helpers import hash_pwd
from flask_user import UserMixin
from pepper.utils import resume_hash, ts


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
    school_id = DB.Column(DB.Integer)
    school_name = DB.Column(DB.String(255))
    special_needs = DB.Column(DB.Text)
    checked_in = DB.Column(DB.Boolean)
    roles = DB.relationship('UserRole', backref='users', lazy='dynamic')
    team = DB.relationship("Team", back_populates="users")
    team_id = DB.Column(DB.Integer, DB.ForeignKey('teams.id', ondelete='CASCADE'))
    mlh_id = DB.Column(DB.Integer)
    access_token = DB.Column(DB.String(255))
    password = DB.Column(DB.String(100))
    type = DB.Column(DB.String(100))
    skill_level = DB.Column(DB.Integer)
    num_hackathons = DB.Column(DB.Integer)
    interests = DB.Column(DB.Text)
    race = DB.Column(DB.String(255))
    med_auth_signature_id = DB.Column(DB.String(255))
    waiver_signature_id = DB.Column(DB.String(255))
    time_applied = DB.Column(DB.DateTime)
    confirmed = DB.Column(DB.Boolean)

    def __init__(self, dict):
        if dict['type'] == 'MLH':  # if creating a MyMLH user
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
            self.mlh_id = dict['data']['id']
            self.type = 'MLH'
            self.access_token = dict['access_token']
            self.resume_uploaded = False
            self.school_id = dict['data']['school']['id']
            self.school_name = dict['data']['school']['name']
        elif dict['type'] == 'local':  # if creating an user through local sign up
            self.email = dict['email']
            self.fname = dict['first_name']
            self.lname = dict['last_name']
            self.birthday = dict['date_of_birth']
            self.status = 'NEW'
            self.created = datetime.utcnow()
            self.major = dict['major']
            self.shirt_size = dict['shirt_size']
            self.dietary_restrictions = dict['dietary_restrictions']
            self.gender = dict['gender']
            self.phone_number = dict['phone_number']
            self.special_needs = dict['special_needs']
            self.checked_in = False
            self.type = 'local'
            self.password = hash_pwd(dict['password'])
            self.resume_uploaded = False
            self.school_name = dict['school_name']
            self.confirmed = False
        else:  # creating a non-OAuth user
            email = dict['email'].lower().strip()
            # email_validation = validate_email(email) #TODO: Email validation
            # if not email_validation['is_valid']:
<<<<<<< HEAD
            #   if email_validation['did_you_mean']:
            #       raise ValueError('%s is an invalid address. Perhaps you meant %s' % (email, email_validation['did_you_mean']))
            #   else:
            #       raise ValueError('%s is an invalid address' % email)
=======
            # 	if email_validation['did_you_mean']:
            # 		raise ValueError('%s is an invalid address. Perhaps you meant %s' % (email, email_validation['did_you_mean']))
            # 	else:
            # 		raise ValueError('%s is an invalid address' % email)
>>>>>>> 24adb014fe9c7bca3fe6ed842bd7ceeeeb054184

            self.email = email
            self.fname = dict['fname']
            self.lname = dict['lname']
            if dict['type'] == 'corporate':  # User account for a recruiter
                self.type = 'corporate'
            else:  # User account for admins
                self.type = 'admin'
                self.password = hash_pwd(dict['password'])

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


class UserRole(DB.Model):
    __tablename__ = 'user_roles'
    id = DB.Column(DB.Integer(), primary_key=True)
    user_id = DB.Column(DB.Integer(), DB.ForeignKey('users.id', ondelete='CASCADE'))
    name = DB.Column(DB.String(64))

    def __init__(self, user_id):
        self.user_id = user_id
