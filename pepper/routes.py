import announcements, users, corporate, static_pages

def configure_routes(app):
	app.add_url_rule('/', 'landing', view_func=users.views.landing, methods=['GET'])

	# Logging in
	app.add_url_rule('/login', 'login', view_func=users.views.login, methods=['GET'])
	app.add_url_rule('/login_local', 'login_local', view_func=users.views.login_local, methods=['GET', 'POST'])
	app.add_url_rule('/register', 'register', view_func=users.views.register, methods=['GET', 'POST'])
	app.add_url_rule('/logout', 'logout', view_func=users.views.logout, methods=['GET'])
	app.add_url_rule('/callback', 'callback', view_func=users.views.callback, methods=['GET'])

	# User action pages
	app.add_url_rule('/dashboard', 'dashboard', view_func=users.views.dashboard, methods=['GET'])
	app.add_url_rule('/confirm', 'confirm-registration', view_func=users.views.confirm_registration, methods=['GET', 'POST'])
	app.add_url_rule('/accept', 'accept-invite', view_func=users.views.accept, methods=['GET', 'POST'])
	app.add_url_rule('/accept/sign', 'sign', view_func=users.views.sign, methods=['GET', 'POST'])

	# Admin Pages
	app.add_url_rule('/admin/create-corp-user', 'create-corp', view_func=users.views.create_corp_user, methods=['GET', 'POST'])
	app.add_url_rule('/admin/debug', 'debug-user', view_func=users.views.debug_user, methods=['GET', 'POST'])
	app.add_url_rule('/admin/initial-create', 'initial-create', view_func=users.views.initial_create, methods=['GET', 'POST'])
	app.add_url_rule('/admin/batch', 'batch-modify', view_func=users.views.batch_modify, methods=['GET', 'POST'])

	# API
	app.add_url_rule('/api/announcements', 'announcements', view_func=announcements.views.announcement_list, methods=['GET'])

	app.add_url_rule('/.well-known/acme-challenge/<path>', view_func=static_pages.views.lets_encrypt_challenge, methods=['GET'])

	# Corporate Portal
	app.add_url_rule('/corp/login', 'corp-login', view_func=corporate.views.login, methods=['GET', 'POST'])
	app.add_url_rule('/corp/login/reset', 'forgot-password', view_func=corporate.views.forgot_password, methods=['GET', 'POST'])
	app.add_url_rule('/corp/login/reset/<token>', 'reset-password', view_func=corporate.views.reset_password, methods=['GET', 'POST'])
	app.add_url_rule('/corp/setup/<token>', 'new-user-setup', view_func=corporate.views.new_user_setup, methods=['GET', 'POST'])

	app.add_url_rule('/corp/dashboard', 'corp-dash', view_func=corporate.views.corporate_dash, methods=['GET', 'POST'])
	app.add_url_rule('/corp/search', 'corp-search', view_func=corporate.views.corporate_search, methods=['GET', 'POST'])
	app.add_url_rule('/corp/view/resume', 'resume-view', view_func=corporate.views.view_resume, methods=['GET'])