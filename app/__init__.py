import re, os
import pandas as pd
from datetime import datetime

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
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_signing import Signatures
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
from app.smtp import Mailer


__version__ = "2.0.0"

app = Flask(__name__)

env = os.environ.get('FLASK_ENV', 'development')
if env == 'production':
    app.config.from_object(ProductionConfig)
elif env == 'testing':
    app.config.from_object(TestingConfig)
else:
    app.config.from_object(DevelopmentConfig)

# print(app.config)

# Assert that app.config['DOMAIN'] is not None
assert app.config['DOMAIN'] is not None, "The 'DOMAIN' configuration must be set. Did you run 'gita-cli init'?"

# Assert that if app.config['REQUIRE_EMAIL_VERIFICATION'] is True, then app.config['SMTP_ENABLED'] must also be True
assert not app.config['REQUIRE_EMAIL_VERIFICATION'] or app.config['SMTP_ENABLED'], \
    "SMTP must be enabled ('SMTP_ENABLED' = True) when email verification is required ('REQUIRE_EMAIL_VERIFICATION' = True). Did you run 'gita-cli init'?"

# Allow us to get access to the end user's source IP
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1)
db = SQLAlchemy()


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
    signatures = Signatures(app, db=db, byte_len=32, rate_limiting=True)

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True) 
    email = db.Column(db.String(1000))
    password = db.Column(db.String(1000))
    username = db.Column(db.String(1000), unique=True)
    active = db.Column(db.Boolean)
    created_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)
    last_password_change = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)
    failed_login_attempts = db.Column(db.Integer, default=0)
    # api_key_id = db.Column(db.Integer, db.ForeignKey('signing.id'), nullable=True)
    api_key = db.Column(db.String(1000), nullable=True)


db.init_app(app=app)
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


# Add rate limits
limiter = Limiter(get_remote_address, app=app, 
    # default_limits=["1000 per day", "50 per hour"],
)
limiter.enabled = app.config['RATE_LIMITS_ENABLED']

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

# Load the JSON file into a DataFrame
df = pd.read_json('data/translation.json')
df2 = pd.read_json('data/verse.json')
df3 = pd.read_json('data/authors.json')
authors = list(df3[['id', 'name']].itertuples(index=False, name=None))

# Regular expressions for different types of references
CHAPTER_REGEX = re.compile(r'^([1-9]|1[0-8])$')
VERSE_REGEX = re.compile(r'^([1-9]|1[0-8])\.([1-9]|[1-9][0-9])$')
RANGE_REGEX = re.compile(r'^([1-9]|1[0-8])\.([1-9]|[1-9][0-9])-([1-9]|[1-9][0-9])$')


def validate_ref_type(reference):
    """
    Validate the reference and determine its type.

    :param reference: str - The reference string to validate.
    :return: tuple - A tuple containing the reference type and additional details.
    """
    if CHAPTER_REGEX.match(reference):
        return 'chapter', int(reference), None, None

    elif VERSE_REGEX.match(reference):
        chapter, verse = map(int, reference.split('.'))
        return 'verse', chapter, verse, None

    elif RANGE_REGEX.match(reference):
        chapter_part, verse_range = reference.split('.')
        chapter = int(chapter_part)
        start_verse, end_verse = map(int, verse_range.split('-'))

        if start_verse >= end_verse:
            raise ValueError("Invalid verse range: start verse should be less than end verse")

        return 'range', chapter, start_verse, end_verse

    else:
        raise ValueError('Invalid reference format')


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



def get_reference(ref_type, chapter, verse, range_end, author_id):
    """
    Fetch the Gita content along with metadata based on the reference type and details.

    :param ref_type: str - The type of reference ('chapter', 'verse', or 'range').
    :param chapter: int - The chapter number.
    :param verse: int - The verse number (if applicable).
    :param range_end: int - The end verse number (if applicable).
    :param author_id: int - The author ID.
    :return: dict - A dictionary containing the text and metadata.
    """
    # Filter df2 based on the reference type to get the verse IDs
    if ref_type == 'chapter':
        verse_ids = df2[df2['chapter_number'] == chapter]['id'].tolist()
        full_reference = str(chapter)
    elif ref_type == 'verse':
        verse_ids = df2[(df2['chapter_number'] == chapter) & (df2['verse_number'] == verse)]['id'].tolist()
        full_reference = f"{chapter}.{verse}"
    elif ref_type == 'range':

        if not range_end:
            raise ValueError('Invalid reference type')

        verse_ids = df2[(df2['chapter_number'] == chapter) & (df2['verse_number'].between(verse, range_end))]['id'].tolist()
        full_reference = f"{chapter}.{verse}-{range_end}"
    else:
        raise ValueError('Invalid reference type')

    if not verse_ids:
        raise ValueError('No verses found for the given reference')

    # Use verse_ids to filter df and get descriptions for the specified author
    filtered_df = df[(df['verse_id'].isin(verse_ids)) & (df['author_id'] == author_id)]
    if filtered_df.empty:
        raise ValueError('No records found for the author and verses')

    # Prepare the output with metadata
    output = {
        "author": filtered_df.iloc[0]['authorName'],
        "text": filtered_df['description'].tolist(),
        "chapter": chapter,
        "verses": verse if ref_type == 'verse' else f"{verse}-{range_end}" if ref_type == 'range' else 'All',
        "reference": full_reference
    }

    return output


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
                    user.active = False
                    flash('Account is locked due to too many failed login attempts.', 'danger')
                db.session.commit()
            error = 'Incorrect password. '

        elif not user.active:
            flash('Your user is currently inactive. If you recently registered, please check your email for a verification link.', "warning")
            return redirect(url_for('login'))

        if error is None:

            login_user(user, remember=False)

            # Update last_login time
            user.last_login = datetime.now()
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

                # Create the users API key
                api_key = signatures.write_key(scope=['api_key'], expiration=365*24, active=True, email=email)
                new_user.api_key = api_key
                # *** But what do we do when it expires?

                db.session.add(new_user)
                db.session.commit()

                # Email notification
                subject='Gita User Registered'

                if app.config["REQUIRE_EMAIL_VERIFICATION"]:
                    # key = signing.write_key_to_database(scope='email_verification', expiration=48, active=1, email=email)
                    key = signatures.write_key(scope=['email_verification'], expiration=48, active=True, email=email)
                    content=f"This email serves to notify you that the user {username} has just been registered for this email address at the Gita API at {app.config['DOMAIN']}. Please verify your email by clicking the following link: {app.config['DOMAIN']}/verify/{key}. Please note this link will expire after 48 hours."
                    flash_msg = f'Successfully created user \'{username.lower()}\'. Please check your email for an activation link.'

                else:
                    content=f"This email serves to notify you that the user {username} has just been registered for this email address at {config['domain']}."
                    flash_msg = f'Successfully created user \'{username.lower()}\'.'
            
                mailer.send_mail(subject=subject, content=content, to_address=email)
                flash(flash_msg, "success")

            except Exception as e: 
                error = f"There was an issue registering the user.{' '+str(e) if env != 'production' else ''}"
            else:
                return redirect(url_for("login"))

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



@app.route('/text', methods=['GET'])
@login_required
def text():
    return render_template('text.html.jinja', 
                            authors=authors,
                            **standard_view_kwargs()
                            )

@app.route('/', methods=['GET'])
def home():
    return render_template('about.html.jinja', **standard_view_kwargs())




@app.route('/api/gita', methods=['GET'])
@limiter.limit("50/hour")
@limiter.limit("200/day")
def get_gita_section():
    signature = request.headers.get('X-API-KEY', None)
    if not signature:
        return jsonify({'error': 'No API key provided'}), 401

    valid = signatures.verify_key(signature, scope=["api_key"])
    if not valid:
        return jsonify({'error': 'Invalid API key'}), 401


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
        gita_content = get_reference(ref_type, chapter, verse, range_end, author_id)

    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    return jsonify({'content': gita_content}), 200

if __name__ == '__main__':
    app.run(debug=True)
