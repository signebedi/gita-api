import os
import click
import secrets
from dotenv import set_key

# Creating a Click group
@click.group()
def cli():
    pass

# Helper function for boolean prompts
def prompt_bool(message, default=None):
    """
    Prompt for a boolean value, interpreting 'y' as True and 'n' as False.
    """
    while True:
        default_str = 'y' if default else 'n'
        value = click.prompt(f"{message} (y/n)", default=default_str, type=str).lower()
        if value in ['y', 'yes']:
            return True
        elif value in ['n', 'no']:
            return False
        else:
            click.echo("Please enter 'y' for yes or 'n' for no.")

@cli.command('init')
@click.argument('env_type', type=click.Choice(['prod', 'dev'], case_sensitive=False))
@click.option('--domain', default=None, help='Domain of the application')
@click.option('--debug', default=None, type=bool, help='Enable or disable debug mode')
@click.option('--secret-key', default=None, help='Secret key for the application')
@click.option('--sqlalchemy-database-uri', default=None, help='Database URI for SQLAlchemy')
@click.option('--hcaptcha-enabled', default=None, type=bool, help='Enable hCaptcha')
@click.option('--smtp-enabled', default=None, type=bool, help='Enable SMTP')
@click.option('--celery-enabled', default=None, type=bool, help='Enable Celery')
@click.option('--rate-limits-enabled', default=None, type=bool, help='Enable rate limits')
@click.option('--max-login-attempts', default=None, type=bool, help='Enable maximum login attempts')
@click.option('--require-email-verification', default=None, type=bool, help='Require email verification')
@click.option('--smtp-mail-server', default=None, help='SMTP Mail Server')
@click.option('--smtp-port', default=None, type=int, help='SMTP Port')
@click.option('--smtp-username', default=None, help='SMTP Username')
@click.option('--smtp-password', default=None, help='SMTP Password')
@click.option('--smtp-from-address', default=None, help='SMTP From Address')
@click.option('--hcaptcha-site-key', default=None, help='hCaptcha Site Key')
@click.option('--hcaptcha-secret-key', default=None, help='hCaptcha Secret Key')
def init_app_command(env_type, domain, debug, secret_key, sqlalchemy_database_uri, hcaptcha_enabled, smtp_enabled, celery_enabled, rate_limits_enabled, max_login_attempts, require_email_verification, smtp_mail_server, smtp_port, smtp_username, smtp_password, smtp_from_address, hcaptcha_site_key, hcaptcha_secret_key):

    if env_type.lower() == 'prod':
        env_file = os.path.join(os.getcwd(), 'instance', 'prod.env')
    else:
        env_file = os.path.join(os.getcwd(), 'instance', 'dev.env')

    # Ensure the instance folder exists
    try:
        os.makedirs(os.path.join(os.getcwd(), 'instance'))
    except OSError:
        pass

    # Ensure both prod.env and dev.env files exist
    for file in ['prod.env', 'dev.env']:
        try:
            open(os.path.join(os.getcwd(), 'instance', file), 'a').close()
        except OSError:
            pass    
        

    # Generate a secret key if not provided
    if not secret_key:
        secret_key = secrets.token_urlsafe(16)

    # Basic configurations
    config = {
        'DOMAIN': domain if domain is not None else click.prompt('Enter DOMAIN', default='http://localhost:5000'),
        'DEBUG': debug if debug is not None else prompt_bool('Is DEBUG mode?', default=False),
        'SECRET_KEY': secret_key,
        'SQLALCHEMY_DATABASE_URI': sqlalchemy_database_uri if sqlalchemy_database_uri is not None else f"sqlite:///{os.path.join(os.getcwd(), 'instance', 'app.sqlite')}",
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'HCAPTCHA_ENABLED': hcaptcha_enabled if hcaptcha_enabled is not None else prompt_bool('Is HCAPTCHA enabled?', default=False),
        'SMTP_ENABLED': smtp_enabled if smtp_enabled is not None else prompt_bool('Is SMTP enabled?', default=False),
        'CELERY_ENABLED': celery_enabled if celery_enabled is not None else prompt_bool('Is CELERY enabled?', default=False),
        'RATE_LIMITS_ENABLED': rate_limits_enabled if rate_limits_enabled is not None else prompt_bool('Is RATE LIMITS enabled?', default=False),
        'MAX_LOGIN_ATTEMPTS': max_login_attempts if max_login_attempts is not None else prompt_bool('Is MAX LOGIN ATTEMPTS enabled?', default=False),
        'REQUIRE_EMAIL_VERIFICATION': require_email_verification if require_email_verification is not None else prompt_bool('Is REQUIRE EMAIL VERIFICATION enabled?', default=False)
    }

    # Additional configurations based on enabled features
    if config['HCAPTCHA_ENABLED']:
        config['HCAPTCHA_SITE_KEY'] = hcaptcha_site_key if hcaptcha_site_key is not None else click.prompt('Enter hCaptcha site key')
        config['HCAPTCHA_SECRET_KEY'] = hcaptcha_secret_key if hcaptcha_secret_key is not None else click.prompt('Enter hCaptcha secret key')
    
    if config['SMTP_ENABLED']:
        config['SMTP_MAIL_SERVER'] = smtp_mail_server if smtp_mail_server is not None else click.prompt('Enter SMTP mail server')
        config['SMTP_PORT'] = smtp_port if smtp_port is not None else click.prompt('Enter SMTP port', type=int)
        config['SMTP_USERNAME'] = smtp_username if smtp_username is not None else click.prompt('Enter SMTP username')
        config['SMTP_PASSWORD'] = smtp_password if smtp_password is not None else click.prompt('Enter SMTP password', hide_input=True)
        config['SMTP_FROM_ADDRESS'] = smtp_from_address if smtp_from_address is not None else click.prompt('Enter SMTP from address')

    # Write configurations to .env
    for key, value in config.items():
        set_key(env_file, key, str(value))

    click.echo(f"Configurations have been set. You can find them at {env_file}.")

if __name__ == "__main__":
    cli()
