# The purpose of this script is to easily print the email confirmation token
# for a user to look up in the logs.

from flask_script import Command, Option

from pepper.utils import serializer


class PrintConfirmEmailTokenCommand(Command):

    option_list = (
        Option('email'),
    )

    def run(self, email):
        print serializer.dumps(email)
