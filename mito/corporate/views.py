from flask import request, render_template, flash, redirect, url_for, g
from flask.ext.login import login_user, current_user, login_required
from mito.users import User
from helpers import check_password
from mito.utils import corp_login_required, roles_required
from sqlalchemy import or_

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
		return redirect(url_for('corp-dash'))

@corp_login_required
@roles_required(['corp', 'admin'])
def corporate_dash():
	return render_template('corporate/dashboard.html')

@corp_login_required
@roles_required(['corp', 'admin'])
def corporate_search():
	universities = request.args.get('u')
	if universities:
		universities = [university.strip() for university in universities.split(',')]
	class_standings = request.args.get('c')
	if class_standings:
		class_standings = [class_standing.strip() for class_standing in class_standings.split(',')]
	majors = request.args.get('m')
	if majors:
		majors = [major.strip() for major in majors.split(',')]
	users = User.query
	if universities:
		users = users.filter(User.school.in_(universities))
		all_users = users.all()
	if majors:
		users = users.filter(User.major.in_(majors))
		all_users = users.all()
	if class_standings:
		users = users.filter(User.class_standing.in_(class_standings))
		all_users = users.all()
	users = users.all()
	return render_template('corporate/results.html', universities=universities, class_standings=class_standings, majors=majors)