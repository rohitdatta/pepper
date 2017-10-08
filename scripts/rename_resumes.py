# The purpose of this file is to fix a bug that went into production where
# user's emails were uploaded to S3 with no first and last name.

from collections import defaultdict

from flask_script import Command

from pepper import hackathon_identity_app
import pepper.settings as settings
from pepper.users.models import User
from pepper.utils import s3_client

class FixResumeCommand(Command):
    def fix_resumes(self):
        named_hashids = []
        named_resumes = defaultdict(list)
        none_hashids = set()
        paginator = s3_client.get_paginator('list_objects_v2')
        page_iterator= paginator.paginate(Bucket=settings.S3_BUCKET_NAME)

        for page in page_iterator:
            for item in page['Contents']:
                key = item['Key']
                if not key.startswith('resumes/'):
                    continue
                key = key[len('resumes/'):]
                data = key[:-4].split(', ', 1)
                lname, (fname, h_id) = data[0], data[1].rsplit(' ', 1)
                h_id = h_id[1:-1]
                if lname == 'None':
                    none_hashids.add(h_id)
                else:
                    named_hashids.append(h_id)
                    named_resumes[h_id].append(key)

        unique_resumes = set(named_hashids)
        print 'Have {} named resumes'.format(len(named_hashids))
        print 'Have {} unique named resumes'.format(len(unique_resumes))
        print 'Have {} None resumes'.format(len(none_hashids))
        repeats = none_hashids.intersection(unique_resumes)
        print 'Set intersection:', len(repeats)
        dont_touch = {key: value for key, value in named_resumes.iteritems() if len(value) > 1}
        print "Don't touch these", len(dont_touch), 'hashids: ', dont_touch
        self.print_stats()
        users = User.query.all()
        new_resumes = {}
        for user in users:
            if user.hashid in none_hashids:
                new_resumes[user.hashid] = u'resumes/{}, {} ({}).pdf'.format(user.lname, user.fname, user.hashid)


        for hashid in none_hashids:
            if hashid in dont_touch:
                continue
            # copy file with new name
            if hashid not in repeats:
                print 'Downloading', hashid, 'reuploading with new name', new_resumes[hashid]
                self.copy_object('resumes/None, None ({}).pdf'.format(hashid), new_resumes[hashid])
            else:
                print 'Not downloading resume', new_resumes[hashid]
            # delete file
            print 'Deleting', 'resumes/None, None ({}).pdf'.format(hashid)
            self.delete_object('resumes/None, None ({}).pdf'.format(hashid))


    def copy_object(self, key, new_key):
        s3_client.copy_object(Bucket=settings.S3_BUCKET_NAME, CopySource='/'.join([settings.S3_BUCKET_NAME, key]), Key=new_key)


    def delete_object(self, key):
        s3_client.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=key)


    def print_stats(self):
        named_hashids = []
        named_resumes = defaultdict(list)
        none_hashids = set()
        paginator = s3_client.get_paginator('list_objects_v2')
        page_iterator= paginator.paginate(Bucket=settings.S3_BUCKET_NAME)

        for page in page_iterator:
            for item in page['Contents']:
                key = item['Key']
                if not key.startswith('resumes/'):
                    continue
                key = key[len('resumes/'):]
                data = key[:-4].split(', ', 1)
                lname, (fname, h_id) = data[0], data[1].rsplit(' ', 1)
                h_id = h_id[1:-1]
                if lname == 'None':
                    none_hashids.add(h_id)
                else:
                    named_hashids.append(h_id)
                    named_resumes[h_id].append(key)

        unique_resumes = set(named_hashids)
        print 'Have {} named resumes'.format(len(named_hashids))
        print 'Have {} unique named resumes'.format(len(unique_resumes))
        print 'Have {} None resumes'.format(len(none_hashids))
        repeats = none_hashids.intersection(unique_resumes)
        print 'Set intersection:', len(repeats)
        dont_touch = {key: value for key, value in named_resumes.iteritems() if len(value) > 1}
        print "Don't touch these", len(dont_touch), 'hashids: ', dont_touch
        

    def run(self):
        #self.fix_resumes()
        self.print_stats()
