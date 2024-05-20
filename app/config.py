import os
import secrets
from dotenv import load_dotenv
load_dotenv()

from datetime import timedelta
class Config:
    DEBUG = True
    SECRET_KEY = secrets.token_hex(32) #os.getenv('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECURITY_PASSWORD_SALT = os.getenv("SECURITY_PASSWORD_SALT")

    # SQLAlchemy pool options
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 1800,  # Recycle connections after 30 minutes
    }

    # SECURITY_EMAIL_VALIDATOR_ARGS = {"check_deliverability": False}
    SECURITY_SEND_REGISTER_EMAIL = False
    SECURITY_POST_REGISTER_VIEW = 'security.login'
    SECURITY_POST_LOGIN_VIEW = 'main.dashboard'
    SECURITY_POST_LOGOUT_VIEW = 'security.login'
    SECURITY_URL_PREFIX = '/api/accounts'
    SECURITY_RECOVERABLE = True
    SECURITY_TRACKABLE = True
    SECURITY_CHANGEABLE = True
    SECURITY_CONFIRMABLE = True
    SECURITY_REGISTERABLE = True
    SECURITY_POST_CONFIRM_VIEW = "/confirmed"
    SECURITY_CONFIRM_ERROR_VIEW = "/confirm-error"
    SECURITY_RESET_VIEW = "/reset-password"
    SECURITY_RESET_ERROR_VIEW = "/reset-password-error"
    SECURITY_LOGIN_ERROR_VIEW = "/login-error"
    SECURITY_POST_OAUTH_LOGIN_VIEW = "/post-oauth-login"
    SECURITY_REDIRECT_BEHAVIOR = "spa"
    SECURITY_VERIFY_URL = "/verify"
    SECURITY_VERIFY_TEMPLATE = 'security/verify.html'
    SECURITY_FRESHNESS =  timedelta(hours=1)
    SECURITY_FRESHNESS_GRACE_PERIOD = timedelta(minutes=30)  # Set grace period to 30 minutes
    SECURITY_CSRF_PROTECT_MECHANISMS = ["session", "basic"]
    SECURITY_CSRF_IGNORE_UNAUTH_ENDPOINTS = True
    SECURITY_CSRF_COOKIE_NAME  = "SECRETE-TOKEN"
    WTF_CSRF_CHECK_DEFAULT = False
    WTF_CSRF_TIME_LIMIT = None
    # SECURITY_REDIRECT_HOST = 'localhost:8080'
    # SECURITY_EMAIL_VALIDATOR = None
    SECURITY_USERNAME_ENABLE = True
    SECURITY_USERNAME_MIN_LENGTH = 5
    SECURITY_USERNAME_MAX_LENGTH = 15
    WEBHOOK_PASSPHRASE = os.getenv('WEBHOOK_PASSPHRASE')
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") 

    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 465
    MAIL_USE_SSL = True
    MAIL_USERNAME = 'praneeth.thilina1991@gmail.com'
    MAIL_PASSWORD = 'wesn wuzk buoa vagr'
