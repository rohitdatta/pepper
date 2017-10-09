from flask.ext.login import login_required, current_user
from flask import request, render_template, redirect, url_for
from helpers import join_team, create_team, rename_team, leave_team, remove_team
from pepper.utils import user_status_blacklist


@login_required
@user_status_blacklist('NEW')
def team():
	if request.method == 'GET':
		if current_user.team_id is None:
			return render_template('teams/manage_team.html')
		else:
			team = current_user.team
			return render_template('teams/team.html', team=team, current_user=current_user)
	else:
		val = request.form.get('button')
		if val == 'join':
			return join_team(request)
		elif val == 'create':
			return create_team(request)
		elif val == 'rename':
			return rename_team(request)
		elif val == 'leave':
			return leave_team(request)
		elif val == 'remove':
			return remove_team(request)
		else:
			return redirect(url_for('team'))
