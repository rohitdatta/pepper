from werkzeug.security import check_password_hash

def check_password(hashed, password):
	return check_password_hash(hashed, password)