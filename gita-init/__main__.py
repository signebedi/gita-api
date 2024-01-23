import os
import click
import secrets
import subprocess
import tempfile
from typing import Union
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

@cli.command('config')
@click.argument('env_type', type=click.Choice(['prod', 'dev'], case_sensitive=False))
@click.option('--domain', default=None, help='Domain of the application')
# @click.option('--debug', default=None, type=bool, help='Enable or disable debug mode')
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
def init_app_command(env_type, domain, secret_key, sqlalchemy_database_uri, hcaptcha_enabled, smtp_enabled, celery_enabled, rate_limits_enabled, max_login_attempts, require_email_verification, smtp_mail_server, smtp_port, smtp_username, smtp_password, smtp_from_address, hcaptcha_site_key, hcaptcha_secret_key):

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
        'DOMAIN': domain if domain is not None else click.prompt('Enter DOMAIN', default='http://127.0.0.1:5000'),
        'SECRET_KEY': secret_key,
        'SQLALCHEMY_DATABASE_URI': sqlalchemy_database_uri if sqlalchemy_database_uri is not None else click.prompt('What is your database connection string?', default=f"sqlite:///{os.path.join(os.getcwd(), 'instance', 'app.sqlite')}"),
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'HCAPTCHA_ENABLED': hcaptcha_enabled if hcaptcha_enabled is not None else prompt_bool('Is HCAPTCHA enabled?', default=False),
        'SMTP_ENABLED': smtp_enabled if smtp_enabled is not None else prompt_bool('Is SMTP enabled?', default=False),
        'CELERY_ENABLED': celery_enabled if celery_enabled is not None else prompt_bool('Is CELERY enabled?', default=False),
        'RATE_LIMITS_ENABLED': rate_limits_enabled if rate_limits_enabled is not None else prompt_bool('Is RATE LIMITS enabled?', default=False),
        'REQUIRE_EMAIL_VERIFICATION': require_email_verification if require_email_verification is not None else prompt_bool('Is REQUIRE EMAIL VERIFICATION enabled?', default=False)
    }

    if max_login_attempts is None:
        max_login_attempts = prompt_bool('Is MAX LOGIN ATTEMPTS enabled?', default=False)

    if max_login_attempts:
        max_login_attempts = click.prompt('How many MAX LOGIN ATTEMPTS?', default=3)
    
    config['MAX_LOGIN_ATTEMPTS'] = max_login_attempts


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


def create_user_and_group(user, group):
    try:
        subprocess.run(['sudo', 'groupadd', group], check=True)
    except subprocess.CalledProcessError:
        click.echo(f"Group '{group}' already exists or could not be created.")

    try:
        subprocess.run(['sudo', 'useradd', '-m', '-g', group, user], check=True)
    except subprocess.CalledProcessError:
        click.echo(f"User '{user}' already exists or could not be created.")

def change_ownership(path, user, group):
    try:
        subprocess.run(['sudo', 'chown', '-R', f'{user}:{group}', path], check=True)
    except subprocess.CalledProcessError:
        click.echo(f"Failed to change ownership of {path}.")

@cli.command('gunicorn')
@click.option('--user', default='gitapi', help='User for the systemd service')
@click.option('--group', default='gitapi', help='Group for the systemd service')
@click.option('--environment', default='production', type=click.Choice(['production', 'development', 'testing']), help='Environment for the systemd service')
@click.option('--working-directory', default=os.getcwd(), help='Working directory for the systemd service')
@click.option('--environment-path', default=os.path.join(os.getcwd(),'venv','bin'), help='Path for the environment')
@click.option('--gunicorn-config', default=os.path.join(os.getcwd(),'gunicorn.conf.py'), help='Gunicorn configuration file')
@click.option('--start-on-success', is_flag=True, help='Start and enable NGINX configuration on success')
def init_systemd_command(user, group, environment, working_directory, environment_path, gunicorn_config, start_on_success):

    systemd_unit = f"""
[Unit]
Description={environment} git-api gunicorn daemon
After=network.target

[Service]
User={user}
Group={group}
WorkingDirectory={working_directory}
Environment='FLASK_ENV={environment}'
Environment='PATH={environment_path}'
ExecStart={environment_path}/gunicorn 'app:app' --config {gunicorn_config}

[Install]
WantedBy=multi-user.target
"""
    # click.echo(systemd_unit)
    unit_file_path = f'/etc/systemd/system/{environment}-git-api.service'
    # click.echo(unit_file_path)

    # Write the systemd unit content to a temporary file
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_file.write(systemd_unit.encode())
        temp_path = tmp_file.name

    # Move the temporary file to the systemd directory
    os.system(f"sudo mv {temp_path} {unit_file_path}")

    os.system('sudo systemctl daemon-reload')

    create_user_and_group(user, group)
    change_ownership(working_directory, user, group)

    if start_on_success:
        os.system(f'sudo systemctl start {environment}-git-api.service')
        os.system(f'sudo systemctl enable {environment}-git-api.service')

    click.echo("Systemd unit file for git-api has been created and daemon reloaded.")
    click.echo("Use the following commands to start and enable the service:")
    click.echo(f"sudo systemctl start {environment}-git-api.service")
    click.echo(f"sudo systemctl enable {environment}-git-api.service")
    if start_on_success:
        click.echo(f"{environment}-git-api.service has been started and enabled.")



if __name__ == "__main__":
    cli()
