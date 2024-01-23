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
Description={environment} gita-api gunicorn daemon
After=network.target

[Service]
User={user}
Group={group}
WorkingDirectory={working_directory}
Environment='FLASK_ENV={environment}'
Environment='PATH={environment_path}'
ExecStart={environment_path}/gunicorn 'wsgi:app' --config {gunicorn_config}

[Install]
WantedBy=multi-user.target
"""
    # click.echo(systemd_unit)
    unit_file_path = f'/etc/systemd/system/{environment}-gita-api.service'
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
        os.system(f'sudo systemctl start {environment}-gita-api.service')
        os.system(f'sudo systemctl enable {environment}-gita-api.service')

    click.echo("Systemd unit file for gita-api has been created and daemon reloaded.")
    click.echo("Use the following commands to start and enable the service:")
    click.echo(f"sudo systemctl start {environment}-gita-api.service")
    click.echo(f"sudo systemctl enable {environment}-gita-api.service")
    if start_on_success:
        click.echo(f"{environment}-gita-api.service has been started and enabled.")

def request_certificates(domain):
    cert_path = f'/etc/letsencrypt/live/{domain}/fullchain.pem'
    key_path = f'/etc/letsencrypt/live/{domain}/privkey.pem'

    # Check if the certificate already exists and is valid
    cert_exists = os.path.isfile(cert_path) and os.path.isfile(key_path)
    if cert_exists:
        # Optionally, you can add more checks here to validate the existing certificate
        print("Certificate already exists.")
        return cert_path, key_path

    # Running certbot to obtain the certificates
    try:
        subprocess.run(['sudo', 'certbot', 'certonly', '--standalone', '-d', domain], check=True)
        return cert_path, key_path
    except subprocess.CalledProcessError as e:
        # Handle errors here
        print(f"Error obtaining certificates: {e}")
        return None, None

@cli.command('nginx')
@click.option('--server-name', prompt='Server name', help='Server name for NGINX')
@click.option('--ssl-enabled', is_flag=True, help='Enable SSL configuration')
@click.option('--request-certbot-certs', is_flag=True, help='Request SSL certificates from Let\'s Encrypt')
@click.option('--ssl-cert-path', default='/etc/ssl/certs/nginx-selfsigned.crt', help='Path to the SSL certificate (ignored if --request-certbot-certs is set)')
@click.option('--ssl-cert-key-path', default='/etc/ssl/private/nginx-selfsigned.key', help='Path to the SSL certificate key (ignored if --request-certbot-certs is set)')
@click.option('--http-port', default=80, help='HTTP port for NGINX (default: 80)')
@click.option('--https-port', default=443, help='HTTPS port for NGINX (default: 443)')
@click.option('--app-port', default=8000, help='Port where the app is running (default: 8000)')
@click.option('--app-ip', default='0.0.0.0', help='IP address of the app (default: 0.0.0.0)')
@click.option('--start-on-success', is_flag=True, help='Start and enable NGINX configuration on success')
@click.option('--retain-default', is_flag=True, help="Retain the default NGINX config in sites-enabled")
def init_nginx_command(server_name, ssl_enabled, request_certbot_certs, ssl_cert_path, ssl_cert_key_path, http_port, https_port, app_port, app_ip, start_on_success, retain_default):
    """
    Note that you will need certbot installed if installing SSL/TLS certificates at runtime.
    """

    if request_certbot_certs:
        ssl_cert_path = f'/etc/letsencrypt/live/{server_name}/fullchain.pem'
        ssl_cert_key_path = f'/etc/letsencrypt/live/{server_name}/privkey.pem'
        subprocess.run(['sudo', 'certbot', 'certonly', '--standalone', '-d', server_name])

    nginx_config = f"""
# Default server block for handling unmatched domain requests on port 80
server {{
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    return 444;  # This will close the connection without responding
}}

upstream app_server {{
    server {app_ip}:{app_port};
}}

# Server block for handling HTTP requests
server {{
    listen                      {http_port};
    listen                      [::]:{http_port};
    server_name                 {server_name};

    {'return 301 https://$server_name$request_uri;' if ssl_enabled else '''
    location / {{
        proxy_pass http://app_server;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}'''
    }
}}
"""

    # Additional server block for handling HTTPS requests, if SSL is enabled
    if ssl_enabled:
        nginx_config += f"""
# Default server block for handling unmatched domain requests on port 443
server {{
    listen 443 ssl default_server;
    listen [::]:443 ssl default_server;
    server_name _;
    ssl_certificate             {ssl_cert_path};
    ssl_certificate_key         {ssl_cert_key_path};
    return 444;  # This will close the connection without responding
}}

# Server block for handling HTTPS requests
server {{
    listen                      {https_port} ssl;
    listen                      [::]:{https_port} ssl;
    server_name                 {server_name};

    ssl_certificate             {ssl_cert_path};
    ssl_certificate_key         {ssl_cert_key_path};

    location / {{
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Server $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_redirect off;
        proxy_pass http://app_server;
    }}
}}
"""


    # Write the NGINX configuration to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.conf') as tmp_file:
        tmp_file.write(nginx_config.encode())
        temp_path = tmp_file.name

    # Move the temporary file to the NGINX configuration directory
    nginx_conf_path = f'/etc/nginx/sites-available/{server_name}'
    os.system(f'sudo mv {temp_path} {nginx_conf_path}')
    os.system(f'sudo ln -s {nginx_conf_path} /etc/nginx/sites-enabled/')

    # Remove default NGINX configuration unless --retain-default is passed
    if not retain_default:
        default_config_path = '/etc/nginx/sites-enabled/default'
        if os.path.exists(default_config_path):
            os.system('sudo rm ' + default_config_path)
            click.echo("Default NGINX configuration removed.")
        else:
            click.echo("No default NGINX configuration found to remove.")

    if start_on_success:
        os.system('sudo nginx -t && sudo systemctl restart nginx')
        os.system('sudo systemctl enable nginx')

    click.echo("NGINX configuration file has been created.")
    click.echo(f"Configuration file path: {nginx_conf_path}")
    if start_on_success:
        click.echo("NGINX has been restarted and enabled.")



if __name__ == "__main__":
    cli()
