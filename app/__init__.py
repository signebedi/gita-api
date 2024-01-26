import re, os
import pandas as pd
from datetime import datetime, timedelta

from flask import (
    Flask, 
    request, 
    jsonify, 
    render_template, 
    url_for,
    current_app,
    flash,
    redirect,
    abort,
    session,
)
from flask_signing import (
    Signatures,
    RateLimitExceeded, 
    KeyDoesNotExist, 
    KeyExpired,
)
from markupsafe import escape
from flask_login import (
    LoginManager, 
    current_user, 
    login_required, 
    UserMixin,
    login_user, 
    logout_user,
)
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash
from flask_sqlalchemy import SQLAlchemy

from app.config import DevelopmentConfig, ProductionConfig, TestingConfig
from app.utils.smtp import Mailer
from app.utils.celery import make_celery
from gita import (
    validate_ref_type,
    get_reference,
    perform_fuzzy_search,
)


__version__ = "4.0.0"

app = Flask(__name__)

env = os.environ.get('FLASK_ENV', 'development')
if env == 'production':
    app.config.from_object(ProductionConfig)
elif env == 'testing':
    app.config.from_object(TestingConfig)
else:
    app.config.from_object(DevelopmentConfig)

if app.config['DEBUG']:
    print(app.config)

# Assert that app.config['DOMAIN'] is not None
assert app.config['DOMAIN'] is not None, "The 'DOMAIN' configuration must be set. Did you run 'gita-init config'?"

# Assert that if app.config['REQUIRE_EMAIL_VERIFICATION'] is True, then app.config['SMTP_ENABLED'] must also be True
assert not app.config['REQUIRE_EMAIL_VERIFICATION'] or app.config['SMTP_ENABLED'], \
    "SMTP must be enabled ('SMTP_ENABLED' = True) when email verification is required ('REQUIRE_EMAIL_VERIFICATION' = True). Did you run 'gita-init config'?"


# Assert that if app.config['COLLECT_USAGE_STATISTICS'] is True, then app.config['CELERY_ENABLED'] must also be True
assert not app.config['COLLECT_USAGE_STATISTICS'] or app.config['CELERY_ENABLED'], \
    "Celery must be enabled ('CELERY_ENABLED' = True) when collecting usage statistics ('COLLECT_USAGE_STATISTICS' = True). Did you run 'gita-init config'?"



# Allow us to get access to the end user's source IP
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1)

# Initialize the database object
db = SQLAlchemy()

# turn off warnings to avoid a rather silly one being dropped in the terminal,
# see https://stackoverflow.com/a/20627316/13301284. 
pd.options.mode.chained_assignment = None

# Instantiate the Mailer object
mailer = Mailer(
    enabled = app.config['SMTP_ENABLED'],
    mail_server = app.config['SMTP_MAIL_SERVER'],
    port = app.config['SMTP_PORT'],
    username = app.config['SMTP_USERNAME'],
    password = app.config['SMTP_PASSWORD'],
    from_address = app.config['SMTP_FROM_ADDRESS'],
)

with app.app_context():
    signatures = Signatures(app, db=db, byte_len=32, rate_limiting=app.config['RATE_LIMITS_ENABLED'])

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True) 
    email = db.Column(db.String(1000))
    password = db.Column(db.String(1000))
    username = db.Column(db.String(1000), unique=True)
    active = db.Column(db.Boolean)
    created_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)
    locked_until = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)
    last_password_change = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)
    failed_login_attempts = db.Column(db.Integer, default=0)
    # api_key_id = db.Column(db.Integer, db.ForeignKey('signing.id'), nullable=True)
    api_key = db.Column(db.String(1000), nullable=True, unique=True)

    usage_log = db.relationship("UsageLog", order_by="UsageLog.id", back_populates="user")

    
# Many to one relationship with User table
class UsageLog(db.Model):
    __tablename__ = 'usage_log'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    endpoint = db.Column(db.String(1000))
    query_params = db.Column(db.String(1000), nullable=True)  # Can we find a way to make this a JSON string or similar format

    user = db.relationship("User", back_populates="usage_log")


db.init_app(app=app)
if app.config['DEBUG'] or app.config['TESTING']:
    with app.app_context():
        db.create_all()

# Arrange standard data to pass to jinja templates
def standard_view_kwargs():
    kwargs = {}
    kwargs['version'] = __version__
    kwargs['config'] = {
        "HCAPTCHA_ENABLED": app.config["HCAPTCHA_ENABLED"],
        "HCAPTCHA_SITE_KEY": app.config["HCAPTCHA_SITE_KEY"] if app.config["HCAPTCHA_ENABLED"] else None,
    }
    kwargs['current_user'] = current_user

    return kwargs


# Create hCaptcha object if enabled
if app.config['HCAPTCHA_ENABLED']:
    from flask_hcaptcha import hCaptcha
    hcaptcha = hCaptcha()
    hcaptcha.init_app(app)

# Setup login manager
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

# Set flask session length. Session lifetime pulled
# from the PERMANENT_SESSION_LIFETIME config.
@app.before_request
def make_session_permanent():
    session.permanent = True

# Load the JSON file into a DataFrame
df = pd.read_json('data/cleaned_data.json')
df2 = pd.read_json('data/authors.json')
authors = list(df2[['id', 'name']].itertuples(index=False, name=None))



if app.config['CELERY_ENABLED']:

    celery = make_celery(app)

    @celery.task
    def send_email_async(subject=None, content=None, to_address=None, cc_address_list=[]):
        return mailer.send_mail(subject=subject, content=content, to_address=to_address, cc_address_list=cc_address_list)


    @celery.task
    def log_api_call(api_key, endpoint, query_params):
        user = User.query.filter_by(api_key=api_key).first()
        if user:
            new_log = UsageLog(
                user_id=user.id,
                timestamp=datetime.utcnow(),
                endpoint=endpoint,
                query_params=str(query_params) 
            )
            db.session.add(new_log)
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                # Placeholder for logging logic

    @celery.task()
    def check_key_rotation():

        # Query for signatures with scope 'api_key'
        keypairs = signatures.rotate_keys(time_until=1, scope="api_key")

        if len(keypairs) == 0:
            return
            
        # For each key that has just been rotated, update the user model with the new key
        for tup in keypairs:
            old_key, new_key = tup
            user = User.query.filter_by(api_key=old_key).first()

            if user:
                user.api_key = new_key
                db.session.commit()


    # If debug mode is set, we'll let the world pull API key usage statistics
    if app.config['DEBUG']:

        from sqlalchemy import create_engine

        @app.route('/stats', methods=['GET'])
        def stats():
           
            # Create an engine to your database
            engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])

            # SQL query or table name
            query = 'SELECT * FROM usage_log'

            # Read data into a Pandas DataFrame
            df = pd.read_sql(query, engine)
            
            # Convert DataFrame to a list of dictionaries
            data = df.to_dict(orient='records')

            return jsonify(data), 200

@app.route('/login', methods=['GET', 'POST'])
def login():

    # we only make this view visible if the user isn't logged in
    if current_user.is_authenticated:
        return redirect(url_for('home'))


    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']


        error = None

        if app.config["HCAPTCHA_ENABLED"]:
            if not hcaptcha.verify():
                flash('There was a Captcha validation error.', "warning")
                return redirect(url_for('login'))


        try:
            user = User.query.filter(User.username.ilike(username.lower())).first()
        except Exception as e:
            flash('There was a problem logging in. Please try again shortly. If the problem persists, contact your system administrator.', "warning")
            return redirect(url_for('login'))


        if not user:
            error = 'Incorrect username. '
        elif not check_password_hash(user.password, password):

            if app.config["MAX_LOGIN_ATTEMPTS"]:
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= app.config["MAX_LOGIN_ATTEMPTS"]:
                    # user.active = False
                    user.locked_until = datetime.utcnow() + timedelta(hours=1)

                    # Calculate the time difference
                    time_diff = user.locked_until - datetime.utcnow()

                    # Extract hours and minutes
                    hours, remainder = divmod(time_diff.seconds, 3600)
                    minutes = remainder // 60

                    # Create a string representing the time delta in hours and minutes
                    time_delta_str = f"{hours} hours, {minutes} minutes" if hours else f"{minutes} minutes"

                    flash(f'Account is locked due to too many failed login attempts. Please try again in {time_delta_str}.', 'danger') 
                db.session.commit()
            error = 'Incorrect password. '

        elif not user.active:
            flash('Your user is currently inactive. If you recently registered, please check your email for a verification link. If you believe this may be a mistake, please contact your system administrator.', "warning")
            return redirect(url_for('login'))


        elif user.locked_until > datetime.utcnow():

            # Calculate the time difference
            time_diff = user.locked_until - datetime.utcnow()

            # Extract hours and minutes
            hours, remainder = divmod(time_diff.seconds, 3600)
            minutes = remainder // 60

            # Create a string representing the time delta in hours and minutes
            time_delta_str = f"{hours} hours, {minutes} minutes" if hours else f"{minutes} minutes"

            flash(f'User is locked. Please try again in {time_delta_str}.', 'danger')
            return redirect(url_for('login'))

        if error is None:

            login_user(user, remember=False)

            # Update last_login time and reset the failed login attempts
            user.last_login = datetime.now()
            user.failed_login_attempts = 0
            db.session.commit()

            flash(f'Successfully logged in user \'{username.lower()}\'.', "success")

            return redirect(url_for('home'))

        flash(error, "warning")


    return render_template('login.html.jinja', 
                            **standard_view_kwargs()
                            )

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash("You have successfully logged out.", "success")
    return redirect(url_for('home'))

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html.jinja', 
                            **standard_view_kwargs()
                            )


@app.route('/create', methods=['GET', 'POST'])
def create_user():

    # we only make this view visible if the user isn't logged in
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        # Placeholder for https://github.com/signebedi/gita-api/issues/15
        # reenter_password = request.form['reenter_password']

        if app.config["HCAPTCHA_ENABLED"]:
            if not hcaptcha.verify():
                flash('There was a Captcha validation error.', "warning")
                return redirect(url_for('login'))

        if username == "":
            username = None
        if email == "":
            email = None

        error = None

        if not username:
            error = 'Username is required. '
        elif not password:
            error = 'Password is required. '
        elif not email:
            error = 'Email is required. '

        elif email and User.query.filter(User.email.ilike(email)).first():
            error = 'Email is already registered. ' 
        elif User.query.filter(User.username.ilike(username.lower())).first():
            error = f'Username {username.lower()} is already registered. ' 

        if error is None:
            try:
                new_user = User(
                            email=email, 
                            username=username.lower(), 
                            password=generate_password_hash(password),
                            active=app.config["REQUIRE_EMAIL_VERIFICATION"] == False,
                        ) 

                # Create the users API key. If Celery disabled, never expire keys 
                expiration = 365*24 app.config['CELERY_ENABLED'] else 0
                api_key = signatures.write_key(scope=['api_key'], expiration=expiration, active=True, email=email)
                new_user.api_key = api_key

                db.session.add(new_user)
                db.session.commit()

                # Email notification
                subject='Gita User Registered'

                if app.config["REQUIRE_EMAIL_VERIFICATION"]:

                    key = signatures.write_key(scope=['email_verification'], expiration=48, active=True, email=email)
                    content=f"This email serves to notify you that the user {username} has just been registered for this email address at the Gita API at {app.config['DOMAIN']}. Please verify your email by clicking the following link: {app.config['DOMAIN']}/verify/{key}. Please note this link will expire after 48 hours."
                    flash_msg = f'Successfully created user \'{username}\'. Please check your email for an activation link.'

                else:
                    content=f"This email serves to notify you that the user {username} has just been registered for this email address at {app.config['DOMAIN']}."
                    flash_msg = f'Successfully created user \'{username}\'.'
            
                # Send email, asynchronously only if celery is enabled
                if app.config['SMTP_ENABLED']:
                    if app.config['CELERY_ENABLED']:
                        send_email_async.delay(subject=subject, content=content, to_address=email)
                    else:
                        mailer.send_mail(subject=subject, content=content, to_address=email)

                flash(flash_msg, "success")

            except Exception as e: 
                error = f"There was an issue registering the user.{' '+str(e) if env != 'production' else ''}"
            else:
                return redirect(url_for('login'))

        flash(f"There was an error in processing your request. {error}", 'warning')

    return render_template('create_user.html.jinja', 
                            **standard_view_kwargs()
                            )


@app.route('/verify/<signature>', methods=('GET', 'POST'))
def verify_email(signature):

    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if not app.config["REQUIRE_EMAIL_VERIFICATION"]:
        return abort(404)

    valid = signatures.verify_key(signature=signature, scope='email_verification')

    if valid:

        s = signatures.get_model().query.filter_by(signature=signature).first()
        email = s.email

        try:
            user = User.query.filter_by(email=str(email)).first() 
            user.active = True
            db.session.commit()

            signatures.expire_key(signature)
            flash(f"Successfully activated user {user.username}.", "success")
            return redirect(url_for('login'))

        except Exception as e: 
            flash (f"There was an error in processing your request.{' '+str(e) if env != 'production' else ''}", 'warning')
    
    return redirect(url_for('login'))



@app.route('/reference', methods=['GET'])
@login_required
def reference():
    return render_template('reference.html.jinja', 
                            authors=authors,
                            **standard_view_kwargs()
                            )

@app.route('/fuzzy', methods=['GET'])
@login_required
def fuzzy():
    return render_template('fuzzy.html.jinja', 
                            authors=authors,
                            **standard_view_kwargs()
                            )


@app.route('/', methods=['GET'])
def home():
    return render_template('about.html.jinja', **standard_view_kwargs())


@app.route('/validate_reference', methods=['POST'])
def validate_reference():
    try:
        # Parse the JSON payload
        data = request.get_json()
        reference = escape(data.get('value'))

        if not reference:
            return jsonify({'status': 'failure', 'msg': 'No reference provided'}), 400

        # Validate the reference
        ref_type, chapter, verse, range_end = validate_ref_type(reference)
        return jsonify({'status': 'success'}), 200

    except ValueError as e:
        return jsonify({'status': 'failure', 'msg': str(e)}), 400


@app.route('/api/reference', methods=['GET'])
def get_gita_section():
    signature = request.headers.get('X-API-KEY', None)
    if not signature:
        return jsonify({'error': 'No API key provided'}), 401

    try:
        valid = signatures.verify_key(signature, scope=["api_key"])

    except RateLimitExceeded:
        return jsonify({'error': 'Rate limit exceeded'}), 429

    except KeyDoesNotExist:
        return jsonify({'error': 'Invalid API key'}), 401

    except KeyExpired:
        return jsonify({'error': 'API key expired'}), 401

    reference = request.args.get('reference')
    author_id = int(request.args.get('author_id', default='16'))

    # Check if reference is provided
    if not reference:
        return jsonify({'error': 'No reference provided'}), 400

    reference = escape(reference.strip())

    try:
        # Validate reference type
        ref_type, chapter, verse, range_end = validate_ref_type(reference)

        # Fetch the relevant content
        gita_content = get_reference(ref_type, chapter, verse, range_end, author_id, df)

        if app.config['COLLECT_USAGE_STATISTICS']:
            # Call the Celery task
            log_api_call.delay(signature, 'reference/', query_params={"reference": reference, "author_id": author_id})

    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    return jsonify({'content': gita_content}), 200



@app.route('/api/fuzzy', methods=['GET'])
def fuzzy_search():
    signature = request.headers.get('X-API-KEY', None)
    if not signature:
        return jsonify({'error': 'No API key provided'}), 401

    try:
        valid = signatures.verify_key(signature, scope=["api_key"]) # if not app.config['TESTING'] else True

    except RateLimitExceeded:
        return jsonify({'error': 'Rate limit exceeded'}), 429

    except KeyDoesNotExist:
        return jsonify({'error': 'Invalid API key'}), 401

    except KeyExpired:
        return jsonify({'error': 'API key expired'}), 401


    search_query = request.args.get('query')

    if not search_query:
        return jsonify({'error': 'No search query provided'}), 400

    search_query = escape(search_query.strip())
    
    # Limit length of the search string
    if len(search_query) > 100:
        return jsonify({'error': 'Query too long. Please keep length at or below 100 chars.'}), 400

    author_id = int(request.args.get('author_id', default='16'))

    # Call the fuzzy search function
    search_results = perform_fuzzy_search(search_query, df=df, author_id=author_id)

    if app.config['COLLECT_USAGE_STATISTICS']:
        # Call the Celery task
        log_api_call.delay(signature, 'fuzzy/', query_params={"query": search_query, "author_id": author_id})


    return jsonify({'content': search_results}), 200



if __name__ == '__main__':
    app.run(debug=True)
