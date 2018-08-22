# Pepper

Pepper is a hackathon application designed to work with MyMLH for sign in.

**This application is under active development and remains in beta. These setup instructions are in no way complete and will be edited once a final version is released. If you have trouble setting it up, please contact me for help.**

## Quickstart

You can deploy this application on Heroku.

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)


## Local Development
It is highly recommended to use a virtualenv to manage dependencies.
1. Create a PostgreSQL database named `pepper`
2. Run `pip install -r requirements.txt`
3. Create a `.env` file with your configuration like the following:
```
    LOG_LEVEL=debug
    SERVICE_NAME=Pepper
    DEBUG=True
    DATABASE_URL='postgresql://Rohit@127.0.0.1:5432/pepper'
    RESUME_HASH_SALT='ur salt here'
    SECRET_KEY='a0th3rS3cr3tH3r3'
    CHECK_IN_SECRET='another secret here'
    REGISTRATION_OPENED=True
    REGISTRATION_CLOSED=True
    PUZZLES_OPEN=True
    CHECK_IN_ENABLED=True
    SENDGRID_API_KEY=''
    HACKATHON_NAME='HackTX'
    MLH_APPLICATION_ID=''
    MLH_SECRET=''
    REQUIRE_SSL=False
    BASE_URL='http://127.0.0.1:5000/'
    GENERAL_INFO_EMAIL='hello@hacktx.com'
    SLACK_TOKEN=''
    MAILGUN_PUB_KEY=''
    S3_BUCKET_NAME=''
    AWS_ACCESS_KEY=''
    AWS_SECRET_KEY=''
    KEEN_PROJECT_ID=''
    KEEN_WRITE_KEY=''
    LETS_ENCRYPT_PATH=''
    LETS_ENCRYPT_PATH_CHALLENGE=''
    CDN_URL=''
    FIREBASE_KEY=''
    RESUMES_LINK=''
    REDIS_URL='127.0.0.1:6379'
    INNOVATION_PORTAL_KEY=''
```
4. Making sure PostgreSQL is running, set up the tables by running `python manage.py db upgrade`
5. Run the server by running `python manage.py runserver`
6. Startup atleast one worker by running `python manage.py runworker` simulatenously.

### Docker setup (Beta):
`docker-compose up`
If you change requirements: `docker-compose build`

### Compile CSS:
`sass --watch pepper/static/scss/:pepper/static/css`

## Explanation of Services

HackTX is a tremendous undertaking and as a result Pepper was built from the ground up to be incredibly powerful.
Pepper is designed to serve as the hub for your hackathon's tech stack before, during, and after the event.
As a result, there are a number of dependencies Pepper depends on, outsourcing much of the work to 3rd parties that can accomplish the task quickly and cheaply.
A list of external dependencies:
- PostgreSQL: A PostgreSQL database can be scaled up to handle the expected max load and if you want quick hosting, Heroku Postgres should do the trick
- SendGrid: Rather than deal with the nightmare that is email delivery, we outsource our email delivery to SendGrid a transactional email provider who offers 12,000 email for free per month (15K with the GitHub student pack)
- MyMLH: Many student hackers apply to multiple hackathons, yet are stuck filling out the same boring name, school, shirt size, etc.
We use MyMLH to make this easy, requiring the applicant to only need to create an account once for all hackathons that use MyMLH.
- Slack: We have an attendee Slack that hooks up to our mobile apps push notification system. When an `@channel` announcement is sent on the `#accouncements` channel, it sends a notification to Pepper, which then pushes out a push notification using...
- Firebase: The Firebase SDK is used on HackTX mobile apps to receive push notifications.
- Mailgun: While this was originally included to do email verification, we decided it wasn't worth it based on the MyMLH process and this is to be removed
- AWS S3: We get a lot of resumes, and running Pepper on a virtual container system means it doesn't make sense to store resumes on the file system.
With AWS S3, we get cheap blob storage, and can easily retrieve resumes for our corporate portal.
- Keen: HackTX runs data pipelines to improve ourselves in future years.
Pepper sends data to Keen to aggregate and allow our various teams to run analytics on.
- Let's Encrypt: We are well aware that hackers are trusting us with personal data, and it is incredibly important to secure it through proper encryption.
Let's Encrypt is a free, automated certificate authority that can issue you an SSL certificate for free.
- AWS CloudFront: Your site will be filled with lots of static files.
Instead of spinning up servers to handle these requests, set up a CDN on CloudFront and reduce your server load.
- Redis: Redis is a key-value in-memory data store.
We use Redis as our queue for a background worker to handle all the jobs that need to get done, such as batch acceptances or confirmation email sending.
If your system is under high load, it's not necessary to immediately perform certain tasks and background workers can handle these jobs instead.
