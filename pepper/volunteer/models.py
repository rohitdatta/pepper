from pepper.app import DB


class Volunteer(DB.Model):
    __tablename__ = 'volunteers'

    id = DB.Column(DB.Integer, primary_key=True)
    email = DB.Column(DB.String)

    def __init__(self, email):
        self.email = email
