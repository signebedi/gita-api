# gita-api
a RESTful Bhagavad Gita API


#### Overview
This API allows users to fetch specific sections from the Bhagavad Gita based on chapter and verse references. It supports fetching an entire chapter (eg. `7`), a specific verse (eg. `7.2`), or a range of verses (eg. `7.2-8`). Based on https://bible-api.com/, using https://github.com/gita/gita. It requires the use of an API key (generated with the creation of a user account) and also features a fuzzy search route.

#### Installation

Here are some installation instructions for Ubuntu 22.04. [Planned work to implement an Ansible Role](https://github.com/signebedi/gita-api/issues/30) will introduce a distribution-agnostic approach, the code below may not work for Nginx and Package Manager package names for non-Debian Linux distributions. 

Start with initial setup, as root.

```bash
apt update && apt upgrade -y
apt install git vim python3 python3-venv certbot nginx
cd /opt
git clone https://github.com/signebedi/gita-api
cd gita-api/
python3 -m venv venv 
source venv/bin/activate
pip install -r requirements/base.txt
```

Install postgres on the localhost if you'd like. You can of course also connect to a remote postgres instance so long as it is configured to receive remote connections. Currently, this application only supports the default sqlite3 and postgres.

```bash
# Install the postgres packages
apt install postgresql postgresql-contrib

# Switch to the postgres user
sudo -i -u postgres

# Create a new user
psql -c "CREATE USER gita_api WITH PASSWORD 'your_password';"

# Create a new database
psql -c "CREATE DATABASE gita_api_db OWNER gita_api;"

# Grant all privileges of the database to the user
psql -c "GRANT ALL PRIVILEGES ON DATABASE gita_api_db TO gita_api;"

# Exit from postgres user
exit
```

You should now be able to set postgres using the connection string `postgresql://gita_api:your_password@localhost/gita_api_db` in the config setup below. Please make sure to replace the your_password to a strong password.

Next we start with configuration. You need to be in your virtualenv for these scripts to work. If you are getting errors when running the scripts below, consider running `source /opt/gita-api/venv/bin/activate` as root. If you are implementing in **development**, follow the following steps.

```bash
# Setup a development configuration
python /opt/gita-api/gita-init config dev

# Setup a development daemon
python /opt/gita-api/gita-init gunicorn --environment development --start-on-success
```
These will open up interfaces to help you generate your application configuration. When in doubt, run `python /opt/gita-api/gita-init config --help` to see available options. This also applies for `python /opt/gita-api/gita-init gunicorn --help` and `python /opt/gita-api/gita-init nginx --help`.


If you are implementing in **production**, follow the following steps

```bash
# Setup a production configuration
python gita-init config prod

# Setup a production daemon
python gita-init gunicorn --start-on-success
```

If you would like to use a local Nginx installation as a reverse proxy, you can use one of the following commands depending on whether you want to set of TLS/SSL.
```bash
# Setup NGINX without TSL/SSL
python gita-init nginx --start-on-success --server-name gita.example.com

# Setup NGINX with TLS/SSL and Let's Encrypt Certificates
python gita-init nginx --start-on-success --server-name gita.example.com --ssl-enabled --request-certbot-certs
```

All of the gita-init commands above can be run headlessly by passing params as options. If you experience a bug with any of these commands, please open an [issue](https://github.com/signebedi/gita-api/issues/new) and provide the commands you ran and outputs you received.  

If you are running in production, always a good call to set up fail2ban, as root.

```bash
# Install the package
apt install -y fail2ban

# Create and configure /etc/fail2ban/jail.local
bash -c 'cat > /etc/fail2ban/jail.local << EOF
[sshd]
enabled = true
bantime = 3600  # Ban IPs for 60 minutes
maxretry = 5  # Ban IPs after 5 failed attempts
EOF'

# Restart Fail2Ban
systemctl restart fail2ban
```

If you want to set up celery to run some tasks asynchronously, you should set the CELERY_ENABLED app config to True. Additionally, you should probably install rabbitmq.

```bash
apt install rabbitmq-server
```

And you can run celery as follows from within /opt/gita-api. If you are getting errors when running the scripts below, consider running `source /opt/gita-api/venv/bin/activate` as root.

The recommended method for initializing celery is to run the gita-init command:

```bash
python gita-init celery --start-on-success
```

And, if you'd like to administer the entire application, you could run the following shorthand at runtime.

Stop:
```bash
systemctl stop production-gita-api-gunicorn && systemctl stop production-gita-api-celery && systemctl stop production-gita-api-celerybeat
```

Restart:
```bash
systemctl restart production-gita-api-gunicorn && systemctl restart production-gita-api-celery && systemctl restart production-gita-api-celerybeat
```


If you'd like to run the commands manually, navigate as root to the working directory and run the following.


```bash
celery -A app.celery worker --loglevel=info --logfile $(pwd)/instance/log/celery.log
```

And you can run celerybeat as follows.

```bash
celery -A app.celery beat --loglevel=info --logfile $(pwd)/instance/log/beat.log
```


#### Contributing

We welcome contributions to the Gita API project. To get started, check out issues tagged as [Help Wanted](https://github.com/signebedi/gita-api/labels/help%20wanted) or [Good First Issues](https://github.com/signebedi/gita-api/labels/good%20first%20issue). These tags indicate areas where your contributions would be particularly valuable. 

If you'd like to make a pull request (PR), please ensure there's an existing issue for your contribution. We prefer discussing potential changes in an issue before receiving a PR. Then, you can [fork the repository](https://github.com/signebedi/gita-api/fork), make your changes in line with the discussed solution, and make appropriate commits, and then submit your PR with a link back to the relevant issue/s. When writing commit messages, please use clear, concise language. Prepend your message with a high-level action summary (e.g., "Added:", "Fixed:", "Removed:") and append the relevant issue number (Ex. `Fixed: Typo in README (#42)`)
