from pepper.app import DB


class Team(DB.Model):
    __tablename__ = 'teams'

    id = DB.Column(DB.Integer, primary_key=True)
    tname = DB.Column(DB.String(255), unique=True)
    users = DB.relationship("User", back_populates="team")

    def __init__(self, name, creator):
        self.tname = name
        self.users = [creator]
