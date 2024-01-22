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




class Config(object):
    DEBUG = False
    SECRET_KEY = "supersecret_dev_key"
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(os.getcwd(), "instance", "app.sqlite")}'
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    HCAPTCHA_ENABLED = False
    SMTP_ENABLED = False
    CELERY_ENABLED = False
    RATE_LIMITS_ENABLED = False

class ProductionConfig(Config):
    SECRET_KEY = collect_secrets_from_file(".secret_key")
    SQLALCHEMY_DATABASE_URI = 'mysql://user@localhost/foo'
    HCAPTCHA_ENABLED = True
    HCAPTCHA_SITE_KEY = ""
    HCAPTCHA_SECRET_KEY = ""
    SMTP_ENABLED = True
    SMTP_MAIL_SERVER = ""
    SMTP_PORT = ""
    SMTP_USERNAME = ""
    SMTP_PASSWORD = ""
    SMTP_FROM_ADDRESS = ""
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

class DevelopmentConfig(Config):
    DEBUG = True

class TestingConfig(Config):
    TESTING = True
