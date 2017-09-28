from pepper.app import DB
from flask import jsonify, request, flash, redirect, url_for, render_template
from models import Volunteer
from pepper.utils import roles_required
from flask.ext.login import login_required


@login_required
@roles_required('admin')
def add_volunteer():
    email = request.form.get('email')
    volunteer = Volunteer(email)
    DB.session.add(volunteer)
    DB.session.commit()

    flash('Successfully added volunteer', 'success')
    return redirect(url_for('volunteer-list'))


@login_required
@roles_required('admin')
def volunteer_list():
    volunteers = Volunteer.query.all()
    return render_template('users/admin/volunteer_list.html', volunteers=volunteers)
