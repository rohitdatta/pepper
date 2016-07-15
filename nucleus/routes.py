import static_pages, announcements, users

def configure_routes(app):
	app.add_url_rule('/', 'landing', view_func=users.views.landing, methods=['GET'])
	app.add_url_rule('/dashboard', 'dashboard', view_func=users.views.dashboard, methods=['GET'])
	app.add_url_rule('/announcements', 'announcements', view_func=announcements.views.announcement_list, methods=['GET'])
	app.add_url_rule('/callback', 'callback', view_func=users.views.callback, methods=['GET'])
	app.add_url_rule('/confirm', 'confirm-registration', view_func=users.views.confirm_registration, methods=['GET', 'POST'])
	app.add_url_rule('/logout', 'logout', view_func=users.views.logout, methods=['GET'])