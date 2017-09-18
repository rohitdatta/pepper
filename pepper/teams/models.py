from pepper.app import DB
from pepper.utils import ts


class Team(DB.Model):
	__tablename__ = 'teams'

	id = DB.Column(DB.Integer, primary_key=True)
	tname = DB.Column(DB.String(255))
	team_count = DB.Column(DB.Integer)
	users = DB.relationship('User', backref='users', lazy='dynamic')

	def __init__(self, dict):
		self.tname = dict['tname']
		self.team_count = dict['team_count']
		self.users = dict['users']