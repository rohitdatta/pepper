import os
import validators
import urllib
from flask import request, jsonify, redirect
from flask_login import current_user, login_required


# sends the current user's full name and database id to the callback provided by the url
@login_required
def auth_user():
    app_id = request.args.get('app_id')
    callback = request.args.get('callback')

    if app_id != os.getenv('INNOVATION_PORTAL_KEY'):
        return jsonify({"error": "Invalid app_id provided"}), 422
    elif callback is None or not validators.url(callback):
        return jsonify({"error": "Invalid callback provided"}), 422
    else:
        data = {"fname": current_user.fname, "lname": current_user.lname, "id": current_user.id}
        return redirect(callback + "?" + urllib.urlencode(data))

