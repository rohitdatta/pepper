from flask import request, render_template, flash, redirect, url_for, g, make_response
from flask.ext.login import login_user, current_user, login_required
from mito.users import User
from helpers import check_password
from mito.utils import corp_login_required, roles_required, s3
from mito import settings
from sqlalchemy import distinct
from mito.app import DB



def login():
	if request.method == 'GET':
		if current_user.is_authenticated:
			return redirect(url_for('corp-dash'))
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
	return render_template('corporate/dashboard.html', user=current_user)

@corp_login_required
@roles_required(['corp', 'admin'])
def corporate_search():
	if request.method == 'GET':
		schools = DB.session.query(distinct(User.school)).all()
		majors = DB.session.query(distinct(User.major)).all()
		class_standings = DB.session.query(distinct(User.class_standing)).all()
		schools, majors, class_standings = [filter(lambda x: x[0] is not None, filter_list) for filter_list in [schools, majors, class_standings]]
		schools, majors, class_standings = [map(lambda x: x[0], filter_list) for filter_list in [schools, majors, class_standings]]
		# [school for school in schools if school != None]
		return render_template('corporate/search.html', schools=schools, majors=majors, class_standings=class_standings)
	else:
		schools = request.form.getlist('schools')
		# if schools:
		# 	schools = [school.strip() for school in schools.split(',')]
		class_standings = request.form.getlist('class_standings')
		# if class_standings:
		# 	class_standings = [class_standing.strip() for class_standing in class_standings.split(',')]
		majors = request.form.getlist('majors')
		# if majors:
		# 	majors = [major.strip() for major in majors.split(',')]
		users = User.query.filter(User.status == 'CONFIRMED')
		if schools:
			users = users.filter(User.school.in_(schools))
			all_users = users.all()
		if majors:
			users = users.filter(User.major.in_(majors))
			all_users = users.all()
		if class_standings:
			users = users.filter(User.class_standing.in_(class_standings))
			all_users = users.all()
		users = users.all()
		return render_template('corporate/results.html', users=users, schools=schools, class_standings=class_standings, majors=majors)

# @corp_login_required
# @roles_required(['corp', 'admin'])
def view_resume():
	hashid = request.args.get('id')
	# user = User.get_with_hashid(hashid)
	# hashid = User.query.filter_by(fname='Rohit').first().hashid
	foo = s3.Object(settings.S3_BUCKET_NAME, 'resumes/{0}-{1}-{2}.pdf'.format(39, 'Datta', 'Rohit')).get()
	User.get_with_hashid(hashid)
	response = make_response(foo['Body'].read())
	response.headers['Content-Type'] = 'application/pdf'
	return response
