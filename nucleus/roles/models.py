from nucleus.app import DB

class Role(DB.Model):
	id = DB.Column(DB.Integer, primary_key=True)
	name = DB.Column(DB.String(50), unique=True)

class UserRoles(DB.Model):
	id = DB.Column(DB.Integer, primary_key=True)
	user_id = DB.Column(DB.Integer, DB.ForeignKey('user.id', ondelete='CASCADE'))
	role_id = DB.Column(DB.Integer, DB.ForeignKey('role.id', ondelete='CASCADE'))