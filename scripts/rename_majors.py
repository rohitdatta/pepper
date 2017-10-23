from pepper.users.models import User
from flask_script import Command
from pepper.app import DB, redis_store
import redis

class FixUsersMajors(Command):
    def run(self):
		all_majors = []
		all_users = User.query.filter_by(school_id=None).all()

		majors_groups = []

		for user in all_users:
			if user.type == 'admin':
				continue;
			if redis_store.get("incorrect_majors:" + user.major) is not None  and redis_store.get("incorrect_majors:" + user.major) is not user.major:
				user.major = redis_store.get("incorrect_majors:" + user.major)
				DB.session.add(user);
				DB.session.commit();
				continue;
			else: 
				majors_groups.append(user)

		for user in majors_groups:
			if redis_store.get("incorrect_majors:" + user.major) is not None and redis_store.get("incorrect_majors:" + user.major) is not user.major:
				user.major = redis_store.get("incorrect_majors:" + user.major)
				DB.session.add(user);
				DB.session.commit();
				continue;
			print(user.major + " " + user.email)
			print("0: Keep")
			print("1: Change")
			option = input('Enter number option: ')
			if option == 1:
				while True:
					decided_major = raw_input('Enter major: ')
					is_decide = raw_input('Do you want to use this major: ' + decided_major + ' - y/n?\n')
					if is_decide == 'Y' or is_decide == 'y':
						break
					elif is_decide == 'N' or is_decide == 'n':
						continue
					else:
						print('Invalid decision - Try again.')
					print('\n')

				redis_store.set("incorrect_majors:" + user.major, decided_major)
				user.major = decided_major
				DB.session.add(user);
				DB.session.commit();
			else:
				redis_store.set("incorrect_majors:" + user.major, user.major)
			if not (user.major in all_majors):
				all_majors.append(user.major)
			print('\n')
			