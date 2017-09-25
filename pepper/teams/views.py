from flask.ext.login import login_required, current_user
from flask import request, render_template, redirect, url_for, flash
from pepper.app import DB
from models import Team

# @login_required
def join_team():
    # GET requests
    if request.method == 'GET':
        team = Team.query.filter_by(id=current_user.team_id).first()
        if team is None:
            return render_template('teams/manage_team.html')
        else:
            return render_template('teams/team.html', team=team)
    # POST requests
    else:
        team = Team.query.filter_by(tname=request.form.get('join_tname')).first()
        # Team doesn't exist so can't join
        if team is None:
            flash('Team does not exist. Try another team name.')
        # Team does exist - check if joinable
        else:
            if team.team_count < 5:
                g.log.info('Joining a team')
                g.log = g.log.bind(tname=team_info['tname'])
                g.log.info('Joining team from local information')
                team.team_count += 1
                # TODO: Check if this adds users to team?
                team.users += current_user
                DB.session.add(team)
                DB.session.commit()
                g.log.info('Successfully created team')

                # TODO: Update user info
                g.log.info('Updating user')
                current_user.team = team
                DB.session.add(current_user)
                DB.session.commit()
                g.log.info('Successfully updated user with team data')

                return render_template('teams/team.html', team=team)
            else:
                flash('Team size has reached capacity.')
        return render_template('teams/manage_team.html')

# @login_required
def create_team():
    # Create team
    team_info = {
        'tname': request.form.get('create_tname'),
        'team_count': 1,
        'users': list(current_user)
    }
    team = Team.query.filter_by(tname=team_info['tname']).first()
    # Team can be created
    if team is None:
        g.log.info('Creating a team')
        g.log = g.log.bind(tname=team_info['tname'])
        g.log.info('Creating a new team from local information')
        team = Team(team_info)
        DB.session.add(team)
        DB.session.commit()
        g.log.info('Successfully created team')

        # TODO: How to update user info?
        g.log.info('Updating user')
        current_user.team = team
        DB.session.add(current_user)
        DB.session.commit()
        g.log.info('Successfully updated user with team data')

        return render_template('teams/team.html', team=team)
    # Team cannot be created
    else:
        flash('Team name not valid',)
        return render_template('teams/manage_team.html')

# @login_required
def leave_team():
    team = Team.query.filter_by(team=current_user.team).first()
    # There is valid team to leave.
    if not (team is None):
        # Delete user data on team
        g.log.info('Leaving team')
        g.log = g.log.bind(tname=team.tname)
        team.team_count -= 1
        g.log.info('Decrement team count')
        # If teamcount is equal to 0, delete team data
        if team.team_count == 0:
            # delete team
            DB.session.delete(team)
            DB.session.commit()
            g.log.info('Successfully deleted team')
        # else update team info
        else:
            team.users.remove(current_user)
            DB.session.add(team)
            DB.session.commit()
            g.log.info('Successfully left team')

        # Update user
        g.log.info('Updating user')
        current_user.team = None
        DB.session.add(current_user)
        DB.session.commit()
        g.log.info('Successfully updated user with no team data')
    return render_template('teams/manage_team.html')

# @login_required
def rename_team():
    new_tname = request.form.get('rename_tname')
    find_team = Team.query.filter_by(tname=new_tname)
    # Team is available
    if find_team is None:
        team = Team.query.filter_by(team=current_user.team).first()
        g.log.info('Renaming team')
        g.log = g.log.bind(tname=new_tname)
        g.log.info('Renaming team from local information')
        team.tname = new_tname
        DB.session.add(team)
        DB.session.commit()
        g.log.info('Successfully renamed team')
    # Team is NOT available
    else:
        flash('Team name not valid')
        return render_template('teams/team.html', team)

