from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from pepper.utils import send_email, s
from pepper import settings
from flask import render_template, url_for, flash

# Create if needed for views but not specifically view stuff