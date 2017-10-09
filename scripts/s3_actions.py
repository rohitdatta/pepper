# The purpose of this file is to fix a bug that went into production where
# user's emails were uploaded to S3 with no first and last name.

from flask_script import Command, Option

from pepper import hackathon_identity_app
import pepper.settings
from pepper.users.models import User
from pepper.utils import s3


class S3Actions(Command):
    def get_all_resumes():
        all_hashids = []
        none_hashids = []
        paginator = s3.get_paginator('list_objects_v2')
        page_iterator = paginator.paginate(Bucket=settings.S3_BUCKET_NAME)

        for page in page_iterator:
            for item in page['Contents']:
                key = item['Key']
                data = key[:-4].split(', ', 1)
                lname, (fname, h_id) = data[0], data[1].rsplit(' ', 1)
                all_hashids.append(h_id)
                if lname == 'None':
                    none_hashids.append(h_id)

        print 'Have {} resumes total'.format(len(all_hashids))
        print 'Have {} unique resumes'.format(len(set(all_hashids)))
        print 'Have {} None resumes'.format(len(none_hashids))
        print 'Have {} unique None resumes'.format(len(set(none_hashids)))

    def run():
        get_all_resumes()
