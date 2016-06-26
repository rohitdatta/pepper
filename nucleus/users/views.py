from flask import redirect, url_for
from flask.ext.login import login_user, logout_user, current_user, login_required
from flask import request, render_template, redirect, url_for


def landing():
	if current_user.is_authenticated:
		return redirect(url_for('dashboard'))
	return render_template("static_pages/index.html")

def dashboard():
	return render_template('users/dashboard.html')