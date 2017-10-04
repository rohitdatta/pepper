import os
import dotenv

# Load environment variable from a .env file
dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from flask.ext.script import Manager
from flask.ext.migrate import Migrate, MigrateCommand
from pepper import hackathon_identity_app, app
from rq import Connection, Worker
import redis

manager = Manager(hackathon_identity_app)

# Migration commands for when you create DB
Migrate(hackathon_identity_app, app.DB)
manager.add_command('db', MigrateCommand)

@manager.command
def runworker():
    redis_url = os.getenv('REDIS_URL')
    redis_connection = redis.from_url(redis_url)
    with Connection(redis_connection):
        worker = Worker(['default'])
        worker.work(logging_level=hackathon_identity_app.config['REDIS_LOG_LEVEL'].upper())

@manager.command
def run(port=5000):
    app.run(port=int(port))


if __name__ == "__main__":
    manager.run()
