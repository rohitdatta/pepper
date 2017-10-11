# The purpose of this script to update database with a CSV

import os
import sys

import psycopg2
import dotenv

# Load environment variable from a .env file
dotenv.load_dotenv('.env')

csv_path = sys.argv[1]
postgres_url = os.getenv('DATABASE_URL')[11:]
user_tokens = postgres_url.split(':')
user_name = user_tokens[0]
password_tokens = user_tokens[1].split('@')
password = password_tokens[0]
db_tokens = password_tokens[1].split('/')
db_url = db_tokens[0]
db_name = db_tokens[1].split('?')[0]

connection = None

rows = open(csv_path).read().split('\n')
id_column, status_column = rows[0].split(',')

try:
    connection = psycopg2.connect(host=db_url, dbname=db_name, user=user_name, password=password)
    cursor = connection.cursor()
    print 'Starting DB connection...'
    for current_row in rows[1:]:
        user_id, status_value = current_row.split(',')

        sql_command = """
        UPDATE users
        SET {} = {}
        WHERE users.id = {};
        """.format(status_column, status_value.upper(), user_id)
        cursor.execute(sql_command)

        print 'Updating user_id={} column={} value={}'.format(user_id, status_column, status_value)
    connection.commit()
except psycopg2.DatabaseError:
    if connection:
        print 'Rolling back...'
        connection.rollback()
finally:
    if connection:
        print 'Closing DB connection...'
        connection.close()
