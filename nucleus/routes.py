import static_pages

def configure_routes(app):
	app.add_url_rule('/', 'index', view_func=static_pages.views.default, methods=['GET'])