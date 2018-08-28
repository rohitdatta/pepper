import validators
import jwt
import datetime
import urllib
from flask import request, jsonify, redirect, url_for, flash
from flask_login import current_user, login_required
from pepper import settings
from pepper.utils import get_default_dashboard_for_role

# sends an access token to the callback provided by the url
@login_required
def auth():
    app_id = request.args.get('app_id')
    callback = request.args.get('callback')
    if app_id != settings.INNOVATION_PORTAL_KEY:
        return jsonify({'error': 'Invalid app_id provided'}), 422
    elif callback is None or not validators.url(callback):
        return jsonify({'error': 'Invalid callback provided'}), 422
    elif current_user.status == 'NEW':
        flash('You must finish registering before starting the puzzle challenge', 'warning')
        return redirect(url_for(get_default_dashboard_for_role()))
    else:
        access_token = {'t': jwt.encode({'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=120), 
            'id': current_user.id, 'fname': current_user.fname, 'lname': current_user.lname}, settings.TOKEN_SEED, algorithm='HS256')}
        return redirect(callback + "?" + urllib.urlencode(access_token))

# returns the current user's full name and database id 
def get_user_info():
    app_id = request.args.get('app_id')
    access_token = request.args.get('t') #token
    if app_id != settings.INNOVATION_PORTAL_KEY:
        return jsonify({'error': 'Invalid app_id provided'}), 422
    try:
        decoded = jwt.decode(access_token, settings.TOKEN_SEED, algorithms=['HS256'])
        return jsonify({'fname': decoded['fname'], 'lname': decoded['lname'], 'id': decoded['id']})
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expired'}), 422
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Token validation failed'}), 422
    except jwt.DecodeError:
        return jsonify({'error': 'Token cannot be decoded'}), 422
    except jwt.InvalidSignatureError:
        return jsonify({'error': 'Token has invalid signature'}), 422
