import announcements, users, corporate

def configure_routes(app):
	app.add_url_rule('/', 'landing', view_func=users.views.landing, methods=['GET'])

	# Logging in
	app.add_url_rule('/login', 'login', view_func=users.views.login, methods=['GET'])
	app.add_url_rule('/logout', 'logout', view_func=users.views.logout, methods=['GET'])
	app.add_url_rule('/callback', 'callback', view_func=users.views.callback, methods=['GET'])

	# User action pages
	app.add_url_rule('/dashboard', 'dashboard', view_func=users.views.dashboard, methods=['GET'])
	app.add_url_rule('/confirm', 'confirm-registration', view_func=users.views.confirm_registration, methods=['GET', 'POST'])
	app.add_url_rule('/accept', 'accept-invite', view_func=users.views.accept, methods=['GET', 'POST'])

	# Admin Pages
	app.add_url_rule('/admin/create-corp-user', 'create-corp', view_func=users.views.create_corp_user, methods=['GET', 'POST'])
	app.add_url_rule('/admin/internal', 'internal-login', view_func=users.views.internal_login, methods=['GET', 'POST'])

	# API
	app.add_url_rule('/api/announcements', 'announcements', view_func=announcements.views.announcement_list, methods=['GET'])

	# Corporate Portal
	app.add_url_rule('/corp/login', 'corp-login', view_func=corporate.views.login, methods=['GET', 'POST'])
	app.add_url_rule('/corp/dashboard', 'corp-dash', view_func=corporate.views.corporate_dash, methods=['GET', 'POST'])
	app.add_url_rule('/corp/search', 'corp-search', view_func=corporate.views.corporate_search, methods=['GET', 'POST'])
	app.add_url_rule('/corp/view/resume', 'resume-view', view_func=corporate.views.view_resume, methods=['GET'])