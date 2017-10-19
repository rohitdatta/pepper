import os
import dotenv

# Load environment variable from a .env file
dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
import redis
from rq import Connection, Worker

from pepper import hackathon_identity_app, app
from scripts.rename_resumes import FixResumeCommand
from scripts.pending_to_waitlisted import PendingToWaitlistedCommand
from scripts.print_confirm_email_token import PrintConfirmEmailTokenCommand
from scripts.strip_whitespace_from_special_needs import StripWhitespaceFromSpecialNeedsCommand

manager = Manager(hackathon_identity_app)

# Migration commands for when you create DB
Migrate(hackathon_identity_app, app.DB)
manager.add_command('db', MigrateCommand)

# add commands from the scripts directory
manager.add_command('fixresumes', FixResumeCommand)
manager.add_command('pending_to_waitlisted', PendingToWaitlistedCommand)
manager.add_command('print_confirm_email_token', PrintConfirmEmailTokenCommand)
manager.add_command('strip_whitespace_from_special_needs', StripWhitespaceFromSpecialNeedsCommand)


@manager.command
def runworker():
    redis_url = os.getenv('REDIS_URL')
    redis_connection = redis.from_url(redis_url)
    with Connection(redis_connection):
        worker = Worker(['default'])
        worker.work(logging_level=hackathon_identity_app.config['REDIS_LOG_LEVEL'].upper())


@manager.command
def run(port=5000):
    hackathon_identity_app.run(port=int(port))


@manager.shell
def make_shell_context():
    from pepper.teams.models import Team
    from pepper.users.models import User, UserRole
    return dict(app=hackathon_identity_app, DB=app.DB, Team=Team, User=User, UserRole=UserRole)


if __name__ == "__main__":
    manager.run()
