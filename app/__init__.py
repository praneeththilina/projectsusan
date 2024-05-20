from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import  current_user
from flask_security.core import Security
from flask_security.datastore import SQLAlchemySessionUserDatastore
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf import CSRFProtect
from flask_mail import Mail
from dotenv import load_dotenv
from .config import Config

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

    from .models import User, Role, PremiumRequest, Notification

    user_datastore = SQLAlchemySessionUserDatastore(db.session, User, Role) # type: ignore
    security = Security(app, user_datastore)

    # Attach Limiter to app
    limiter.init_app(app)
    
    # Register Blueprints or routes
    from .routes import register_blueprints
    register_blueprints(app)


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
    def inject_notification_count():
        if current_user.is_authenticated:
            notification_count = Notification.query.filter_by(user_id=current_user.id, read=False).count()
        else:
            notification_count = 0
        return dict(notification_count=notification_count)

    return app
