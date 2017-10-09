from pepper.app import DB


class Announcement(DB.Model):
	__tablename__ = 'announcements'

	id = DB.Column(DB.Integer, primary_key=True)
	text = DB.Column(DB.Text)
	timestamp = DB.Column(DB.DateTime)

	def __init__(self, text, ts):
		self.text = text
		self.timestamp = ts
