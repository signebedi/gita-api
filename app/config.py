import os
from dotenv import load_dotenv
from datetime import timedelta
from markupsafe import Markup

# Determine environment
env = os.getenv('FLASK_ENV', 'development')

if not env == 'testing':
    env_file = 'prod.env' if env == 'production' else 'dev.env'
    env_file_path = os.path.join(os.getcwd(), 'instance', env_file)

    if os.path.exists(env_file_path):
        load_dotenv(env_file_path)

    else:
        print("Error: env file not found. Did you run 'gita-init config'?")
        exit(1)

else: env_file_path=""

class Config(object):
    CONFIG_FILE_PATH = env_file_path
    SITE_NAME = os.getenv('SITE_NAME', 'Gita API')
    HOMEPAGE_CONTENT = Markup(os.getenv('HOMEPAGE_CONTENT', '<p>The Gita API seeks provide granular programmatic access to the text of the Bhagavad Gita ("The Song of God"), one of Hinduism\'s foundational religious texts with a significant following by non-Hindu peoples, especially academics. We ask you to register an account to help us understand usage trends, prevent abuse of the API, and meet generally-accepted best practices for API design. Beyond your email, we will not ask you for any personal information, nor provide any of this information to commercial third parties. For more information about the application, see the source code at <a href="https://github.com/signebedi/gita-api">https://github.com/signebedi/gita-api</a>.</p>'))
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
        'broker_connection_retry_on_startup': False,
        # Schedule for periodic tasks
        'beat_schedule':{
            "run-key-check-daily": {
                "task": "app.check_key_rotation",
                'schedule': 45.0,  # For rapid testing
                # 'schedule': 3600.0,  # Hourly
                # 'schedule': 86400.0,  # Daily
            }
        },

    }

    RATE_LIMITS_ENABLED = os.getenv('RATE_LIMITS_ENABLED', 'False') == 'True'
    # Rate limiting period should be an int corresponding to the number of minutes
    RATE_LIMITS_PERIOD = timedelta(minutes=int(os.getenv('RATE_LIMITS_PERIOD', 1)))
    RATE_LIMITS_MAX_REQUESTS = int(os.getenv('RATE_LIMITS_MAX_REQUESTS', 50))

    # MAX_LOGIN_ATTEMPTS = lambda: default_get_max_login_attempts("False")
    MAX_LOGIN_ATTEMPTS = int(os.getenv('MAX_LOGIN_ATTEMPTS', "0"))
    REQUIRE_EMAIL_VERIFICATION = os.getenv('REQUIRE_EMAIL_VERIFICATION', 'False') == 'True'
    # Permanent session lifetime should be an int corresponding to the number of minutes
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=int(os.getenv('PERMANENT_SESSION_LIFETIME', 360)))
    COLLECT_USAGE_STATISTICS = os.getenv('COLLECT_USAGE_STATISTICS', 'False') == 'True'
    DISABLE_NEW_USERS = os.getenv('DISABLE_NEW_USERS', 'False') == 'True'

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

    # Defaults to True / Enabled in production, with more stringent default settings
    RATE_LIMITS_ENABLED = os.getenv('RATE_LIMITS_ENABLED', 'True') == 'True'
    RATE_LIMITS_PERIOD = timedelta(minutes=int(os.getenv('RATE_LIMITS_PERIOD', 1)))
    RATE_LIMITS_MAX_REQUESTS = int(os.getenv('RATE_LIMITS_MAX_REQUESTS', 10))

    # MAX_LOGIN_ATTEMPTS = lambda: default_get_max_login_attempts(5)
    MAX_LOGIN_ATTEMPTS = int(os.getenv('MAX_LOGIN_ATTEMPTS', "5")) 
    REQUIRE_EMAIL_VERIFICATION = os.getenv('REQUIRE_EMAIL_VERIFICATION', 'True') == 'True'

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(os.getcwd(), "instance", "DEV_app.sqlite")}'

class TestingConfig(Config):
    TESTING = True
    DOMAIN = 'http://127.0.0.1:5000'
    SECRET_KEY = 'supersecret_test_key'
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    HCAPTCHA_ENABLED = False
    SMTP_ENABLED = False

    CELERY_ENABLED = False

    RATE_LIMITS_ENABLED = True
    MAX_LOGIN_ATTEMPTS = False
    REQUIRE_EMAIL_VERIFICATION = False
    PERMANENT_SESSION_LIFETIME = timedelta(hours=int(os.getenv('PERMANENT_SESSION_LIFETIME', 6)))


