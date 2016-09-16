from flask import request, render_template, redirect, url_for
from pepper import settings

def default(template='index'):
	template = template if template.endswith('.html') else template+'.html'
	return render_template("static_pages/"+template, is_redirect = request.args.get('redirected'))

def internal_error(e):
	import traceback
	log.error(traceback.format_exc())
	return render_template('static_pages/500.html'), 500

def page_not_found(e):
	return render_template('static_pages/500.html', title='Oops, page not found'), 404

def lets_encrypt_challenge(path):
	if path == settings.LETS_ENCRYPT_PATH:
		return settings.LETS_ENCRYPT_PATH_CHALLENGE
	else:
		return 'Undefined'