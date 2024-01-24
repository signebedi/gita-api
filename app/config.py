import os
from dotenv import load_dotenv


# Determine environment
env = os.getenv('FLASK_ENV', 'development')
env_file = 'prod.env' if env == 'production' else 'dev.env'
env_file_path = os.path.join(os.getcwd(), 'instance', env_file)

if os.path.exists(env_file_path):
    load_dotenv(env_file_path)

else:
    print("Error: env file not found. Did you run 'gita-init config'?")
    exit(1)

def default_get_max_login_attempts(default):
    x = os.getenv('MAX_LOGIN_ATTEMPTS', default)
    return False if x == "False" else x


class Config(object):
    CONFIG_FILE_PATH = env_file_path
    DOMAIN = os.getenv('DOMAIN', 'http://127.0.0.1:5000')
    DEBUG = os.getenv('DEBUG', 'False') == 'True'
    SECRET_KEY = os.getenv('SECRET_KEY', 'supersecret_dev_key')
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI', f'sqlite:///{os.path.join(os.getcwd(), "instance", "app.sqlite")}')
    SQLALCHEMY_TRACK_MODIFICATIONS = os.getenv('SQLALCHEMY_TRACK_MODIFICATIONS', 'False') == 'True'
    
    HCAPTCHA_ENABLED = os.getenv('HCAPTCHA_ENABLED', 'False') == 'True'
    HCAPTCHA_SITE_KEY = os.getenv('HCAPTCHA_SITE_KEY', None)
    HCAPTCHA_SECRET_KEY = os.getenv('HCAPTCHA_SECRET_KEY', None)

    SMTP_ENABLED = os.getenv('SMTP_ENABLED', 'False') == 'True'
    SMTP_MAIL_SERVER = os.getenv('SMTP_MAIL_SERVER')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 25))    
    SMTP_USERNAME = os.getenv('SMTP_USERNAME')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
    SMTP_FROM_ADDRESS = os.getenv('SMTP_FROM_ADDRESS')

    CELERY_ENABLED = os.getenv('CELERY_ENABLED', 'False') == 'True'
    CELERY_CONFIG = {
        'broker_url': os.getenv('CELERY_BROKER_URL', "pyamqp://guest@localhost//"),
        'result_backend': os.getenv('CELERY_RESULT_BACKEND', "rpc://"),
        'task_serializer': 'json',
        'accept_content': ['json'],
        'result_serializer': 'json',
        'enable_utc': True,
    }

    RATE_LIMITS_ENABLED = os.getenv('RATE_LIMITS_ENABLED', 'False') == 'True'
    MAX_LOGIN_ATTEMPTS = lambda: default_get_max_login_attempts("False")
    REQUIRE_EMAIL_VERIFICATION = os.getenv('REQUIRE_EMAIL_VERIFICATION', 'False') == 'True'

class ProductionConfig(Config):
    # The DOMAIN is meant to fail in production if you have not set it
    DOMAIN = os.getenv('DOMAIN', None)

    # Defaults to True in production
    HCAPTCHA_ENABLED = os.getenv('HCAPTCHA_ENABLED', 'True') == 'True'
    HCAPTCHA_SITE_KEY = os.getenv('HCAPTCHA_SITE_KEY', None)
    HCAPTCHA_SECRET_KEY = os.getenv('HCAPTCHA_SECRET_KEY', None)
    
    # Defaults to True in production
    SMTP_ENABLED = os.getenv('SMTP_ENABLED', 'False') == 'True'

    # Defaults to True in production
    CELERY_ENABLED = os.getenv('CELERY_ENABLED', 'True') == 'True'

    # Defaults to True / Enabled in production
    RATE_LIMITS_ENABLED = os.getenv('RATE_LIMITS_ENABLED', 'True') == 'True'
    MAX_LOGIN_ATTEMPTS = lambda: default_get_max_login_attempts(5)
    REQUIRE_EMAIL_VERIFICATION = os.getenv('REQUIRE_EMAIL_VERIFICATION', 'True') == 'True'

class DevelopmentConfig(Config):
    DEBUG = True

class TestingConfig(Config):
    TESTING = True
