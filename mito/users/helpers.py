from werkzeug.security import generate_password_hash

def hash_pwd(password):
    return generate_password_hash(password)