
from nucleus.app import DB

class User(DB.Model):
	__tablename__ = 'users'

	id = DB.Column(DB.Integer, primary_key=True)