import static_pages, announcements

def configure_routes(app):
	app.add_url_rule('/', 'index', view_func=static_pages.views.default, methods=['GET'])
	app.add_url_rule('/announcements', 'announcements', view_func=announcements.views.announcement_list, methods=['GET'])