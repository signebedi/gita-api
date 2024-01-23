import os, secrets

def collect_secrets_from_file(filename):
    try:
        os.makedirs(os.path.join(os.getcwd(), 'instance'))
    except OSError:
        pass
    filepath = os.path.join(os.getcwd(), 'instance', filename)
    if not os.path.exists(filepath):
        with open(filepath, 'w') as f: 
            # create, write, and return secret key if doesn't exist
            secret_key = secrets.token_urlsafe(16)
            f.write(secret_key)
            return secret_key
    
    with open(filepath, 'r') as f: 
        return f.readlines()[0].strip()

"""
Read SMTP credentials.
This expects a text file with each of the following items in the following order, each on their own line without
any quotation marks.
> smtp_mail_server
> smtp_port
> smtp_username
> smtp_password
> smtp_from_address

If it does not exist, we simply pass an empty list of the expected length
"""

filepath = os.path.join(os.getcwd(), 'instance', '.smtp_creds')
if os.path.exists(filepath):
    with open(filepath, 'r') as f: 
        smtp_creds = [x.strip() for x in f.readlines()[:5]]
else:
    smtp_creds = [None for x in range (5)]


class Config(object):
    DOMAIN = "http://localhost:5000"
    DEBUG = False
    SECRET_KEY = "supersecret_dev_key"
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(os.getcwd(), "instance", "app.sqlite")}'
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    HCAPTCHA_ENABLED = False
    SMTP_ENABLED = False
    SMTP_MAIL_SERVER = smtp_creds[0] or None
    SMTP_PORT = smtp_creds[1] or None
    SMTP_USERNAME = smtp_creds[2] or None
    SMTP_PASSWORD = smtp_creds[3] or None
    SMTP_FROM_ADDRESS = smtp_creds[4] or None
    CELERY_ENABLED = False
    RATE_LIMITS_ENABLED = False
    MAX_LOGIN_ATTEMPTS = False
    REQUIRE_EMAIL_VERIFICATION=False

class ProductionConfig(Config):
    DOMAIN = "https://READ_FROM_ENV.com"
    SECRET_KEY = collect_secrets_from_file(".secret_key")
    # SQLALCHEMY_DATABASE_URI = 'mysql://user@localhost/foo'
    HCAPTCHA_ENABLED = True
    HCAPTCHA_SITE_KEY = collect_secrets_from_file(".hcaptcha_site_key")
    HCAPTCHA_SECRET_KEY = collect_secrets_from_file(".hcaptcha_secret_key")
    SMTP_ENABLED = True
    CELERY_ENABLED = True
    CELERY_CONFIG={
        'broker_url': "pyamqp://guest@localhost//",
        'result_backend':"rpc://",
        'task_serializer':'json',
        'accept_content':['json'],
        'result_serializer':'json',
        'enable_utc':True,
    },
    RATE_LIMITS_ENABLED = True
    # Placeholder - define not-in-memory storage for Flask-Limiter,
    # see https://flask-limiter.readthedocs.io#configuring-a-storage-backend.
    MAX_LOGIN_ATTEMPTS=5
    REQUIRE_EMAIL_VERIFICATION=True

class DevelopmentConfig(Config):
    DEBUG = True

class TestingConfig(Config):
    TESTING = True
