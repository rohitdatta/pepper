from pepper.users.models import User
from flask_script import Command
from pepper.app import DB, redis_store
import redis

class FixUsersMajors(Command):

    def decide(self, msg):
        return raw_input("{} [yN] ".format(msg)).strip().lower() == 'y'

    def run(self):
        all_users = User.query.filter(User.major != None).order_by(User.major).all()

        for user in all_users:
            if user.type == 'admin':
                continue
            corrected_users_redis_key = 'corrected_major_ids'
            if redis_store.sismember(corrected_users_redis_key, user.id):
                continue
            incorrect_majors_redis_key = 'incorrect_majors:{}'.format(user.major)
            print("Fixing user {}, {} ({})".format(user.lname, user.fname, user.hashid))
            print('Major: {}'.format(user.major))
            if redis_store.scard(incorrect_majors_redis_key) > 0:
                majors = list(redis_store.smembers(incorrect_majors_redis_key))
                while True:
                    print('0: Keep')
                    for i, major in enumerate(majors):
                        print('{}: {}'.format(i + 1, major))
                    print('{}: Choose a new name'.format(len(majors) + 1))
                    option = raw_input("Enter a number: ")
                    try:
                        option = int(option)
                        if option == 0:
                            if self.decide("Are you sure you want to keep {}?".format(user.major)):
                                if self.decide("Is this major correct for all users?"):
                                    all_majors = User.query.filter_by(major=user.major).all()
                                    for u in all_majors:
                                        redis_store.sadd(corrected_users_redis_key, u.id)
                                else:
                                    redis_store.sadd(corrected_users_redis_key, user.id)
                                break
                        elif option > 0 and option <= len(majors):
                            new_major = majors[option - 1]
                            if self.decide("Are you sure you want to use {}?".format(new_major)):
                                user.major = new_major
                                DB.session.add(user)
                                DB.session.commit()
                                redis_store.sadd(corrected_users_redis_key, user.id)
                                break
                        elif option == len(majors) + 1:
                            new_major = raw_input("Please enter the corrected major: ")
                            if self.decide("Are you sure you want to use {}?".format(new_major)):
                                redis_store.sadd(incorrect_majors_redis_key, new_major)
                                if self.decide("Do you want to use this major for all majors of this spelling?"):
                                    all_misspellings = User.query.filter_by(major=user.major).all()
                                    for u in all_misspellings:
                                        u.major = new_major
                                        DB.session.add(u)
                                        redis_store.sadd(corrected_users_redis_key, u.id)
                                    DB.session.commit()
                                else:
                                    user.major = new_major
                                    DB.session.add(user)
                                    DB.session.commit()
                                    redis_store.sadd(corrected_users_redis_key, user.id)
                                break
                        else:
                            # invalid number
                            raise ValueError()
                    except:
                        print("Please enter a number between 0 and {}".format(len(majors) + 1))
            else:
                while True:
                    print('0: Keep')
                    print('1: Choose a new name')
                    option = raw_input("Enter a number: ")
                    if option == '0':
                        if self.decide('Are you sure you want to keep {}?'.format(user.major)):
                            if self.decide('Do you want to use this major for all majors of this spelling?'):
                                all_majors = User.query.filter_by(major=user.major).all()
                                for u in all_majors:
                                    redis_store.sadd(corrected_users_redis_key, u.id)
                            else:
                                redis_store.sadd(corrected_users_redis_key, user.id)
                            break
                    elif option == '1':
                        new_major = raw_input("Please enter the corrected major: ")
                        if self.decide("Are you sure you want to use {}?".format(new_major)):
                            redis_store.sadd(incorrect_majors_redis_key, new_major)
                            if self.decide("Do you want to use this major for all majors of this spelling?"):
                                all_misspellings = User.query.filter_by(major=user.major).all()
                                for u in all_misspellings:
                                    u.major = new_major
                                    DB.session.add(u)
                                    redis_store.sadd(corrected_users_redis_key, u.id)
                                DB.session.commit()
                            else:
                                user.major = new_major
                                DB.session.add(user)
                                DB.session.commit()
                                redis_store.sadd(corrected_users_redis_key, user.id)
                            break
