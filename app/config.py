import os
from dotenv import load_dotenv


# Determine environment
env = os.getenv('FLASK_ENV', 'development')
env_file = 'prod.env' if env == 'production' else 'dev.env'
env_file_path = os.path.join(os.getcwd(), 'instance', env_file)

if os.path.exists(env_file_path):
    load_dotenv(env_file_path)

else:
    print("Error: env file not found. Are you sure you ran 'flask init-app'?")
    exit(1)

class Config(object):
    DOMAIN = os.getenv('DOMAIN', "http://localhost:5000")
    DEBUG = os.getenv('DEBUG', 'False') == 'True'
    SECRET_KEY = os.getenv('SECRET_KEY', 'supersecret_dev_key')
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI', f'sqlite:///{os.path.join(os.getcwd(), "instance", "app.sqlite")}')
    SQLALCHEMY_TRACK_MODIFICATIONS = os.getenv('SQLALCHEMY_TRACK_MODIFICATIONS', 'False') == 'True'
    HCAPTCHA_ENABLED = os.getenv('HCAPTCHA_ENABLED', 'False') == 'True'
    SMTP_ENABLED = os.getenv('SMTP_ENABLED', 'False') == 'True'
    SMTP_MAIL_SERVER = os.getenv('SMTP_MAIL_SERVER')
    SMTP_PORT = os.getenv('SMTP_PORT')
    SMTP_USERNAME = os.getenv('SMTP_USERNAME')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
    SMTP_FROM_ADDRESS = os.getenv('SMTP_FROM_ADDRESS')
    CELERY_ENABLED = os.getenv('CELERY_ENABLED', 'False') == 'True'
    RATE_LIMITS_ENABLED = os.getenv('RATE_LIMITS_ENABLED', 'False') == 'True'
    MAX_LOGIN_ATTEMPTS = os.getenv('MAX_LOGIN_ATTEMPTS', 'False') == 'True'
    REQUIRE_EMAIL_VERIFICATION = os.getenv('REQUIRE_EMAIL_VERIFICATION', 'False') == 'True'

class ProductionConfig(Config):
    DOMAIN = os.getenv('PROD_DOMAIN', "https://your-production-domain.com")
    SECRET_KEY = os.getenv('PROD_SECRET_KEY', 'your-production-secret-key')
    HCAPTCHA_ENABLED = os.getenv('PROD_HCAPTCHA_ENABLED', 'True') == 'True'
    HCAPTCHA_SITE_KEY = os.getenv('PROD_HCAPTCHA_SITE_KEY', 'your-hcaptcha-site-key')
    HCAPTCHA_SECRET_KEY = os.getenv('PROD_HCAPTCHA_SECRET_KEY', 'your-hcaptcha-secret-key')
    SMTP_ENABLED = os.getenv('PROD_SMTP_ENABLED', 'True') == 'True'
    # Assuming you have similar environment variables for these:
    SMTP_MAIL_SERVER = os.getenv('PROD_SMTP_MAIL_SERVER')
    SMTP_PORT = int(os.getenv('PROD_SMTP_PORT', 25))    
    SMTP_USERNAME = os.getenv('PROD_SMTP_USERNAME')
    SMTP_PASSWORD = os.getenv('PROD_SMTP_PASSWORD')
    SMTP_FROM_ADDRESS = os.getenv('PROD_SMTP_FROM_ADDRESS')
    CELERY_ENABLED = os.getenv('PROD_CELERY_ENABLED', 'True') == 'True'
    CELERY_CONFIG = {
        'broker_url': os.getenv('CELERY_BROKER_URL', "pyamqp://guest@localhost//"),
        'result_backend': os.getenv('CELERY_RESULT_BACKEND', "rpc://"),
        'task_serializer': 'json',
        'accept_content': ['json'],
        'result_serializer': 'json',
        'enable_utc': True,
    }
    RATE_LIMITS_ENABLED = os.getenv('PROD_RATE_LIMITS_ENABLED', 'True') == 'True'
    MAX_LOGIN_ATTEMPTS = int(os.getenv('PROD_MAX_LOGIN_ATTEMPTS', 5))
    REQUIRE_EMAIL_VERIFICATION = os.getenv('PROD_REQUIRE_EMAIL_VERIFICATION', 'True') == 'True'

class DevelopmentConfig(Config):
    DEBUG = True

class TestingConfig(Config):
    TESTING = True
