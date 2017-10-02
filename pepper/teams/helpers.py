from models import Team
from pepper.app import DB
from pepper.utils import user_status_blacklist
from datetime import datetime

from flask.ext.login import current_user, login_required
from flask import g, render_template, redirect, url_for, flash

@login_required
@user_status_blacklist('NEW')
def join_team(request):
    if request.form.get('join_tname') == '':
        flash('Please enter a team name.','warning')
        return redirect(url_for('team'))
    team = Team.query.filter_by(tname=request.form.get('join_tname')).first()
    # Team doesn't exist so can't join
    if team is None:
        flash('Team does not exist. Try another team name.', 'warning')
    elif len(team.users) < 5:
        g.log.info('Joining a team')
        g.log = g.log.bind(tname=request.form.get('join_tname'))
        g.log.info('Joining team from local information')
        current_user.time_team_join = datetime.utcnow()
        team.users.append(current_user)
        try:
            DB.session.add(team)
            DB.session.commit()
        except Exception as e:
            g.log.error('error occurred while joining team: {}'.format(e))
            flash('The team you were trying to join either does not exist or is full. If this error occurs multiple times, please contact us', 'error')
            return redirect(request.url)
        g.log.info('Successfully created team')
        flash('Successfully joined team.','success')
    else:
        flash('Team size has reached capacity.','warning')
    return redirect(url_for('team'))

@login_required
@user_status_blacklist('NEW')
def create_team(request):
    if request.form.get('create_tname') == '':
        flash('Please enter a team name.','warning')
        return redirect(request.url)
    if current_user.team_id is not None:
        flash('You cannot create a team if you are already in one!', 'error')
        return redirect(request.url)
    # Create team
    tname = request.form.get('create_tname')
    team = Team.query.filter_by(tname=tname).first()
    # Team can be created
    if team is None:
        g.log.info('Creating a team')
        g.log = g.log.bind(tname=tname)
        g.log.info('Creating a new team from local information')
        current_user.is_leader = True
        current_user.time_team_join = datetime.utcnow()
        team = Team(tname, current_user)
        try:
            DB.session.add(team)
            DB.session.commit()
        except Exception as e:
            g.log.error('error occurred while creating team: {}'.format(e))
            flash('The team you were trying to create already exists. If this error occurs multiple times, please contact us', 'error')
            return redirect(request.url)
        g.log.info('Successfully created team')
        flash('Successfully created team!','success')
        return redirect(url_for('team'))
    # Team cannot be created
    else:
        flash('This team name already exists! Please try another name.','warning')
        return redirect(request.url)

@login_required
@user_status_blacklist('NEW')
def leave_team(request):
    team = Team.query.filter_by(tname=current_user.team.tname).first()
    # There is valid team to leave.
    if team is None:
        flash('You are not part of a team', 'error')
    else:
        # Delete user data on team
        g.log.info('Leaving team')
        g.log = g.log.bind(tname=team.tname)
        team.users.remove(current_user)
        if team.users:
            if current_user.is_leader:
                current_user.is_leader = False
                team.users = sorted(
                    team.users,
                    key=lambda x: x.time_team_join, reverse=True
                )
                temp_user = team.users[len(team.users)-1]
                temp_user.is_leader = True
            DB.session.add(team)
            DB.session.commit()
            g.log.info('Successfully left team')
        else:
            # delete an empty team
            try:
                if current_user.is_leader:
                    current_user.is_leader = False
                DB.session.delete(team)
                DB.session.commit()
            except Exception as e:
                g.log.error('error leaving team: {}'.format(e))
                flash('An error occurred. Please try again.', 'error')
                return redirect(request.url)
            g.log.info('Successfully deleted team')
        g.log.info('current user team: {}'.format(current_user.team_id))
        flash('You have left the team.','success')
    return redirect(url_for('team'))

@login_required
@user_status_blacklist('NEW')
def rename_team(request):
    if not current_user.is_leader:
        flash('Cannot rename team.','warning')
        return redirect(url_for('team'))
    if request.form.get('rename_tname') == '':
        flash('Please enter a team name.','warning')
        return redirect(url_for('team'))
    new_tname = request.form.get('rename_tname')
    find_team = Team.query.filter_by(tname=new_tname).first()
    # Team is available
    if find_team is None:
        team_name = current_user.team.tname
        current_user.team = Team.query.filter_by(tname=team_name).first()
        current_user.team.tname = new_tname
        DB.session.add(current_user.team)
        DB.session.commit()
        g.log.info('Successfully renamed team')
        flash('Team has successfully been renamed to ' + new_tname + '.','success')
        return render_template('teams/team.html', team=current_user.team, user=current_user)
    # Team is NOT available
    else:
        g.log.info('TEAM IS NOT AVAILABLE')
        flash('Team name has already used. Please pick a different name.','warning')
    return redirect(url_for('team', team=current_user.team, user=current_user))

