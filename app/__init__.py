from flask import Flask, render_template

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import  current_user
from flask_security.core import Security
from flask_security.datastore import SQLAlchemySessionUserDatastore
from flask_security.utils import hash_password
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from flask_wtf import CSRFProtect
from flask_mail import Mail
from dotenv import load_dotenv
from .config import Config
from datetime import datetime
from pytz import timezone
from functools import wraps

db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
mail = Mail()
cache = Cache(config={'CACHE_TYPE': 'simple'})
load_dotenv()

# Initialize Limiter
limiter = Limiter(key_func=get_remote_address, 
                    default_limits=["1000 per day", "20 per hour"],
                    storage_uri="memory://"
                )




def rate_limit_if_not_admin(limit_string):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if current_user.has_role('admin'):
                # Admin user, skip rate limiting
                return f(*args, **kwargs)
            else:
                # Apply rate limiting for non-admin users
                return limiter.limit(limit_string, key_func=lambda: current_user.id)(f)(*args, **kwargs)
        return wrapped
    return decorator


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    # cache.init_app(app)
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    mail.init_app(app)

    from .models import User, Role, Notification, BotFuelPackage, BotFuelTransaction, IDCounter, PremiumPackage

    user_datastore = SQLAlchemySessionUserDatastore(db.session, User, Role) # type: ignore
    security = Security(app, user_datastore)

    # Attach Limiter to app
    limiter.init_app(app)
    
    # Register Blueprints or routes
    from .routes import register_blueprints
    register_blueprints(app)
    from .webhook import register_blueprint
    register_blueprint(app)
    from .custom_webhook import register_blueprint
    register_blueprint(app)
    from .custom_wh_alert import register_blueprint
    register_blueprint(app)
    from .premiums import register_blueprint
    register_blueprint(app)
    from .subscription import register_blueprint
    register_blueprint(app)
    from .profile import register_blueprint
    register_blueprint(app)


    @app.errorhandler(404)
    def page_not_found(error):
        return render_template('server_err/404.html'), 404

    # Custom error handler for 502 errors
    @app.errorhandler(505)
    def bad_gateway_error(error):
        return render_template('server_err/505.html'), 505

    @app.errorhandler(405)
    def method_not_allowed_error(error):
        return render_template('server_err/405.html'), 405

    @app.context_processor
    def inject_pending_count():
        pending_count = BotFuelTransaction.query.filter(
            BotFuelTransaction.successful == False
        ).count()
        return dict(pending_count=pending_count)

    @app.context_processor
    def inject_user_timezone():
        def format_last_login():
            if current_user.is_authenticated and current_user.last_login_at:
                user_timezone = timezone(current_user.timezone if current_user.timezone else 'UTC')
                last_login_at = current_user.last_login_at.astimezone(user_timezone)
                return last_login_at.strftime('%Y-%m-%d %H:%M')
            return None
        return dict(format_last_login=format_last_login)


    @app.context_processor
    def inject_notification_count():
        if current_user.is_authenticated:
            notification_count = Notification.query.filter_by(user_id=current_user.id, read=False).count()
        else:
            notification_count = 0
        return dict(notification_count=notification_count)
    
    @app.before_request
    def before_request():
        if current_user.is_authenticated:
            current_user.check_and_apply_pending_premium()
    
    # Remove X-Powered-By header to hide server software information
    @app.after_request
    def remove_x_powered_by(response):
        response.headers.pop('X-Powered-By', None)
        return response



    @app.before_request
    def create_default_data():
        initialize_default_data(user_datastore)

    def initialize_default_data(user_datastore):
        with app.app_context():
            if not Role.query.filter_by(name='user').first():
                user_role = user_datastore.create_role(name='user', permissions='user-read, user-write')
                db.session.add(user_role)
            
            if not Role.query.filter_by(name='admin').first():
                admin_role = user_datastore.create_role(name='admin', permissions='admin-read, admin-write')
                db.session.add(admin_role)
            
            if not BotFuelPackage.query.all():
                packages = [
                    BotFuelPackage(name='Small Pack', amount=100, cost_usdt=10), # type: ignore
                    BotFuelPackage(name='Medium Pack', amount=300, cost_usdt=30), # type: ignore
                    BotFuelPackage(name='Large Pack', amount=1000, cost_usdt=100) # type: ignore
                ]
                db.session.bulk_save_objects(packages)   

            if PremiumPackage.query.count() == 0:
                sample_packages = [
                    PremiumPackage(name="Silver Package", duration_days=30, price=100.0), # type: ignore
                    PremiumPackage(name="Gold Package", duration_days=60, price=175.0), # type: ignore
                    PremiumPackage(name="Platinum Package", duration_days=90, price=250.0), # type: ignore
                ]
                db.session.bulk_save_objects(sample_packages)

                # Initialize the ID counter if it doesn't exist
            if IDCounter.query.count() == 0:
                db.session.add(IDCounter(counter=0))
                db.session.commit()
         
            
            db.session.commit()

            if not User.query.filter_by(email='admin@mail.com').first():
                admin_user = user_datastore.create_user(
                    email='admin@mail.com',
                    password=hash_password('password'),
                    confirmed_at=datetime.now(),
                    roles=['admin']
                )
                db.session.add(admin_user)
            
            db.session.commit()
    
            # Assign role 'user' to users who do not have any roles yet
            users_without_role = User.query.filter(~User.roles.any()).all()
            user_role = Role.query.filter_by(name='user').first()
            if user_role:
                for user in users_without_role:
                    user.roles.append(user_role)
                db.session.commit()

                    
    return app

