release: python manage.py db upgrade
web: gunicorn pepper:hackathon_identity_app
worker: python manage.py runworker
