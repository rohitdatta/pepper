# Script to trim the extra whitespace rom the special needs ield

from flask_script import Command
from sqlalchemy.orm import load_only

from pepper.users.models import User
from pepper.app import DB


class StripWhitespaceFromSpecialNeedsCommand(Command):
    def run(self):
        users = User.query.options(load_only("special_needs")).all()
        for user in users:
            user.special_needs = user.special_needs.strip() if user.special_needs else ''
            DB.session.add(user)
        DB.session.commit()
