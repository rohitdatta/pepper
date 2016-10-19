import announcements, users, corporate, static_pages, api, volunteer

def configure_routes(app):
	app.add_url_rule('/', 'landing', view_func=users.views.landing, methods=['GET'])

	# Logging in
	app.add_url_rule('/login', 'login', view_func=users.views.login, methods=['GET'])
	app.add_url_rule('/alt/login', 'login_local', view_func=users.views.login_local, methods=['GET', 'POST'])
	app.add_url_rule('/alt/login/reset', 'forgot-password', view_func=users.views.forgot_password, methods=['GET', 'POST'])
	app.add_url_rule('/alt/login/reset/<token>', 'reset-password', view_func=users.views.reset_password, methods=['GET', 'POST'])
	app.add_url_rule('/register', 'register_local', view_func=users.views.register_local, methods=['GET', 'POST'])
	app.add_url_rule('/register/confirm/<token>', 'confirm-account', view_func=users.views.confirm_account, methods=['GET'])
	app.add_url_rule('/logout', 'logout', view_func=users.views.logout, methods=['GET'])
	app.add_url_rule('/callback', 'callback', view_func=users.views.callback, methods=['GET'])

	# User action pages
	app.add_url_rule('/edit_profile', 'edit_profile', view_func=users.views.edit_profile, methods=['GET', 'POST'])
	app.add_url_rule('/dashboard', 'dashboard', view_func=users.views.dashboard, methods=['GET'])
	app.add_url_rule('/confirm', 'confirm-registration', view_func=users.views.confirm_registration, methods=['GET', 'POST'])
	app.add_url_rule('/profile', 'update-profile', view_func=users.views.edit_resume, methods=['GET', 'POST'])
	app.add_url_rule('/profile/resume', 'view-own-resume', view_func=users.views.view_own_resume, methods=['GET'])
	app.add_url_rule('/refresh', 'refresh-mlh-data', view_func=users.views.refresh_from_MLH, methods=['GET'])
	app.add_url_rule('/accept', 'accept-invite', view_func=users.views.accept, methods=['GET', 'POST'])
	app.add_url_rule('/accept/sign', 'sign', view_func=users.views.sign, methods=['GET', 'POST'])

	# Admin Pages
	app.add_url_rule('/admin/create-corp-user', 'create-corp', view_func=users.views.create_corp_user, methods=['GET', 'POST'])
	app.add_url_rule('/admin/debug', 'debug-user', view_func=users.views.debug_user, methods=['GET', 'POST'])
	app.add_url_rule('/admin/initial-create', 'initial-create', view_func=users.views.initial_create, methods=['GET', 'POST'])
	app.add_url_rule('/admin/batch', 'batch-modify', view_func=users.views.batch_modify, methods=['GET', 'POST'])
	app.add_url_rule('/admin/send-email', 'send-email', view_func=users.views.send_email_to_users, methods=['GET', 'POST'])
	app.add_url_rule('/admin/volunteer-list', 'volunteer-list', view_func=volunteer.views.volunteer_list, methods=['GET'])
	app.add_url_rule('/admin/add-volunteer', 'add-volunteer', view_func=volunteer.views.add_volunteer, methods=['POST'])
	app.add_url_rule('/admin/reject', 'reject-users', view_func=users.views.reject_users, methods=['GET', 'POST'])
	app.add_url_rule('/admin/modify-user', 'modify-user', view_func=users.views.modify_user, methods=['GET', 'POST'])

	# API
	app.add_url_rule('/api/announcements', 'announcements', view_func=announcements.views.announcement_list, methods=['GET'])
	app.add_url_rule('/api/announcements/create', 'create-announcement', view_func=announcements.views.create_announcement, methods=['POST'])
	app.add_url_rule('/api/partners', 'partners', view_func=api.views.partner_list, methods=['GET'])
	app.add_url_rule('/api/schedule', 'schedule', view_func=api.views.schedule, methods=['GET'])
	app.add_url_rule('/api/check-in', 'check-in-api', view_func=api.views.check_in, methods=['GET', 'POST'])
	app.add_url_rule('/api/passbook', 'passbook', view_func=api.views.passbook, methods=['POST'])

	app.add_url_rule('/.well-known/acme-challenge/<path>', view_func=static_pages.views.lets_encrypt_challenge, methods=['GET'])

	# Corporate Portal
	app.add_url_rule('/corp/login', 'corp-login', view_func=corporate.views.login, methods=['GET', 'POST'])
	app.add_url_rule('/corp/login/reset', 'corp-forgot-password', view_func=corporate.views.forgot_password, methods=['GET', 'POST'])
	app.add_url_rule('/corp/login/reset/<token>', 'corp-reset-password', view_func=corporate.views.reset_password, methods=['GET', 'POST'])
	app.add_url_rule('/corp/setup/<token>', 'new-user-setup', view_func=corporate.views.new_user_setup, methods=['GET', 'POST'])

	app.add_url_rule('/corp/dashboard', 'corp-dash', view_func=corporate.views.corporate_dash, methods=['GET', 'POST'])
	app.add_url_rule('/corp/search', 'corp-search', view_func=corporate.views.corporate_search, methods=['GET'])
	app.add_url_rule('/corp/search/results', 'search-results', view_func=corporate.views.search_results, methods=['POST'])
	app.add_url_rule('/corp/view/resume', 'resume-view', view_func=corporate.views.view_resume, methods=['GET'])

	app.add_url_rule('/corp/download/all-resumes', 'all-resume-download', view_func=corporate.views.download_all_resumes, methods=['GET'])