# Pepper

Pepper is a hackathon application designed to work with MyMLH for sign in. Using virtualenv is highly suggested to manage the dependencies.

**This application is under active development and remains in beta. These setup instructions are in no way complete and will be edited once a final version is released. If you have trouble setting it up, please contact me for help.**

Create a PostgreSQL database named `pepper` and then run `pip install -r requirements.txt` and then create a `.env` file with your configuration like the following:


    LOG_LEVEL=debug
    SERVICE_NAME=Pepper
    DEBUG=True
    DATABASE_URL='postgresql://Rohit@127.0.0.1:5432/pepper'
    NONCE_SECRET='y0ur_n0nc3_s3cr3t'
    HASHIDS_SALT='a salt'
    SECRET_KEY='y0ur_s3cr3t_k3y'
    SENDGRID_API_KEY=''
    HACKATHON_NAME='HackTX'
    MLH_APPLICATION_ID=''
    MLH_SECRET=''
    BASE_URL='http://127.0.0.1:5000/'
    GENERAL_INFO_EMAIL='hello@hacktx.com'
    SLACK_TOKEN=''
    MAILGUN_PUB_KEY=''
    S3_BUCKET_NAME=''
    AWS_ACCESS_KEY=''
    AWS_SECRET_KEY=''

Create the tables by running `python manage.py db upgrade`

Run the server by running `python manage.py runserver`