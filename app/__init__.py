from flask import Flask, render_template

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import  current_user
from flask_security.core import Security
from flask_security.datastore import SQLAlchemySessionUserDatastore
from flask_security.utils import hash_password
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf import CSRFProtect
from flask_mail import Mail
from dotenv import load_dotenv
from .config import Config
from datetime import datetime
from pytz import timezone

db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
mail = Mail()
load_dotenv()

# Initialize Limiter
limiter = Limiter(key_func=get_remote_address, 
                  default_limits=["10 per second"],
                  storage_uri="memory://"
                  )

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    mail.init_app(app)

    from .models import User, Role, PremiumRequest, Notification, PremiumPlan

    user_datastore = SQLAlchemySessionUserDatastore(db.session, User, Role) # type: ignore
    security = Security(app, user_datastore)

    # Attach Limiter to app
    limiter.init_app(app)
    
    # Register Blueprints or routes
    from .routes import register_blueprints
    register_blueprints(app)
    from .webhook import register_blueprint
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
        pending_count = PremiumRequest.query.filter(
            PremiumRequest.approved == False,
            PremiumRequest.rejected == False
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

            
            # Add PremiumPlan data
            if not PremiumPlan.query.filter_by(name='1 Month').first():
                plan_1_month = PremiumPlan(name='1 Month', valid_days=30) # type: ignore
                db.session.add(plan_1_month)

            if not PremiumPlan.query.filter_by(name='2 Months').first():
                plan_2_months = PremiumPlan(name='2 Months', valid_days=60) # type: ignore
                db.session.add(plan_2_months)

            if not PremiumPlan.query.filter_by(name='3 Months').first():
                plan_3_months = PremiumPlan(name='3 Months', valid_days=90) # type: ignore
                db.session.add(plan_3_months)

            db.session.commit()
            
    return app

