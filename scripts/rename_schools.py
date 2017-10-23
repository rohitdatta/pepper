from pepper.users.models import User
from flask_script import Command
from pepper.app import DB, redis_store
from collections import Counter, defaultdict
import redis

class FixUsersSchoolNames(Command):
    def run(self):
		all_colleges = []
		all_users = User.query.filter_by(school_id=None).all()

		edu_groups = defaultdict(list)
		non_edus = []

		# Add edus:schools stuff
		
		for user in all_users:
			if user.type == 'admin' or user.status == 'NEW':
				continue;
			if redis_store.get("incorrect_school_names:" + user.school_name) is not None:
				user.school_name = redis_store.get("incorrect_school_names:" + user.school_name)
				DB.session.add(user);
				DB.session.commit();
				continue;
			if "edu" in user.email:
				school_edu = user.email.split("@")
				if redis_store.get("email_to_school:" + school_edu[1]) is not None:
					user.school_name = redis_store.get("email_to_school:" + school_edu[1])
					DB.session.add(user);
					DB.session.commit();
				else:
					edu_groups[school_edu[1]].append(user)
			else: 
				non_edus.append(user)

		for key, value in edu_groups.iteritems():
			count_schools_dict = Counter()
			for user in value:
				count_schools_dict[user.school_name]+=1
			sorted_schools_dict = count_schools_dict.most_common(5)
			print(key)
			temp = 0

			for x in sorted_schools_dict:
				print("(" + str(temp) + "): " + x[0])
				temp+=1
			print("" + str(temp) + ": Customize Name")
			key = input('Enter number key: ')
			if key < len(sorted_schools_dict):
				decided_name = sorted_schools_dict[key][0]
				print(decided_name)
			else:
				while True:
					decided_name = raw_input('Enter school name: ')
					is_decide = raw_input('Do you want to use this name: ' + decided_name + ' - Y/N')
					if is_decide == 'Y' or is_decide == 'y':
						break
					elif is_decide == 'N' or is_decide == 'n':
						continue
					else:
						print('Invalid decision - Try again.')
					print('\n')
			redis_store.set("email_to_school:" + key, decided_name)
			for user in value:
				redis_store.set("incorrect_school_names:"+ user.school_name,decided_name)
				user.school_name = decided_name
				DB.session.add(user);
			DB.session.commit();
			all_colleges.append(decided_name)
			print('\n')

		for user in non_edus:
			if redis_store.get("incorrect_school_names:" + user.school_name) is not None:
				user.school_name = redis_store.get("incorrect_school_names:" + user.school_name)
				DB.session.add(user);
				DB.session.commit();
				continue;
			print(user.school_name + " " + user.email)
			print("0: Keep")
			print("1: Change")
			key = input('Enter number key: ')
			if key == 1:
				while True:
					decided_name = raw_input('Enter school name: ')
					is_decide = raw_input('Do you want to use this name: ' + decided_name + ' - y/n?\n')
					if is_decide == 'Y' or is_decide == 'y':
						break
					elif is_decide == 'N' or is_decide == 'n':
						continue
					else:
						print('Invalid decision - Try again.')
					print('\n')
				user.school_name = decided_name
				DB.session.add(user);
				DB.session.commit();
			if not (user.school_name in all_colleges):
				all_colleges.append(user.school_name)
			print('\n')
			