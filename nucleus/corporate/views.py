from flask import request, render_template, flash, redirect, url_for
from flask.ext.login import login_user
from nucleus.users import User
from helpers import check_password


def login():
	if request.method == 'GET':
		return render_template('corporate/login.html')
	else:
		email = request.form['email']
		password = request.form['password']
		user = User.query.filter_by(email=email).first()
		if user is None:
			flash("We couldn't find an account related with this email. Please verify the email entered.", "warning")
			return redirect(url_for('login'))
		elif not check_password(user.password, password):
			flash("Invalid Password. Please verify the password entered.", 'warning')
			return redirect(url_for('login'))
		login_user(user, remember=True)
		flash('Logged in successfully!', 'success')
		return redirect(request.args.get('next') or url_for('dashboard'))