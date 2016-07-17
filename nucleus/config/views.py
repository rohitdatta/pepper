from nucleus.app import redis_store

def toggle_application_period():
	open = redis_store.get('applications_open') or True
	redis_store.set('applications_open', not open)