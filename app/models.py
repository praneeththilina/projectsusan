from flask_security.core import UserMixin, RoleMixin
from flask_security.datastore import AsaList
from sqlalchemy.ext.mutable import MutableList
from . import db
import uuid
from datetime import datetime
from .crypto_utils import encrypt, decrypt
from flask_security.models import fsqla_v3 as fsqla
from sqlalchemy import event
from sqlalchemy.orm import relationship

fsqla.FsModels.set_db_info(db)

class Role(db.Model, fsqla.FsRoleMixin):
    pass
class PremiumPackage(db.Model):
    __tablename__ = 'premium_packages'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    duration_days = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)

class PendingPremium(db.Model):
    __tablename__ = 'pending_premiums'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    package_id = db.Column(db.Integer, db.ForeignKey('premium_packages.id'), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    approved = db.Column(db.Boolean, default=False)
    
    user = db.relationship('User', back_populates='pending_premiums')
    package = db.relationship('PremiumPackage')

class User(db.Model, fsqla.FsUserMixin):
    public_id = db.Column(db.String(256), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    _api_key = db.Column(db.String(256), nullable=True)
    _api_secret = db.Column(db.String(256), nullable=True)
    expire_date = db.Column(db.DateTime)
    settings = db.relationship("UserSettings", uselist=False, back_populates="user")
    notifications = db.relationship('Notification', back_populates='user', cascade="all, delete-orphan")
    avatar = db.Column(db.String(50), default='avatar1.svg')
    timezone = db.Column(db.String(50), nullable=True)
    terms_accepted = db.Column(db.Boolean, default=False)
    terms_accepted_at = db.Column(db.DateTime)
    _fuel_balance = db.Column(db.Integer, default=0, nullable=True)
    premium = db.Column(db.Boolean, default=False)  # Indicating if the user is Premium
    webhook_url = db.relationship('WebhookURL', backref='user', uselist=False)
    pending_premiums = db.relationship('PendingPremium', back_populates='user', cascade="all, delete-orphan")
    following = db.relationship('Subscription', foreign_keys='Subscription.follower_id', backref='follower', lazy='dynamic')
    followers = db.relationship('Subscription', foreign_keys='Subscription.premium_user_id', backref='premium_user', lazy='dynamic')

    @property
    def is_premium(self):
        return self.premium and self.expire_date and self.expire_date > datetime.now()

    def check_and_apply_pending_premium(self):
        if self.premium and self.expire_date:
            now = datetime.now()
            if self.expire_date < now:
                pending_premium = PendingPremium.query.filter_by(user_id=self.id, approved=True).order_by(PendingPremium.start_date).first()
                if pending_premium:
                    self.expire_date = pending_premium.end_date
                    db.session.delete(pending_premium)
                    db.session.commit()
                else:
                    self.premium = False
                    db.session.commit()


    @property
    def fuel_balance(self):
        return self._fuel_balance

    @fuel_balance.setter
    def fuel_balance(self, value):
        self._fuel_balance = value


    @property
    def api_key(self):
        return decrypt(self._api_key) if self._api_key else None

    @api_key.setter
    def api_key(self, value):
        self._api_key = encrypt(value)

    @property
    def api_secret(self):
        return decrypt(self._api_secret) if self._api_secret else None

    @api_secret.setter
    def api_secret(self, value):
        self._api_secret = encrypt(value)
        
    def __str__(self):
        return self.username

class WebhookURL(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True)
    url = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())


class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    premium_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    # follower = db.relationship('User', foreign_keys=[follower_id], backref='following')
    # premium_user = db.relationship('User', foreign_keys=[premium_user_id], backref='followers')
class BotFuelPackage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    cost_usdt = db.Column(db.Float, nullable=False)

    def __str__(self):
        return self.name

class BotFuelTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref='fuel_transactions')
    package_id = db.Column(db.Integer, db.ForeignKey('bot_fuel_package.id'))
    package = db.relationship('BotFuelPackage', backref='transactions')
    payment_method = db.Column(db.String(20), nullable=False)
    pay_id = db.Column(db.String(80), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    successful = db.Column(db.Boolean, default=False)

    def __str__(self):
        return f"Transaction by {self.user.username} for {self.package.name}"
    
class TradingStrategy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    description = db.Column(db.String(255))
    config = db.Column(db.JSON)

class IDCounter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    counter = db.Column(db.Integer, nullable=False)

    def __init__(self, counter=0):
        self.counter = counter
class Trade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trade_id = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    pair = db.Column(db.String(30))
    comment = db.Column(db.String(10))
    orderid = db.Column(db.String(30))
    status = db.Column(db.String(15))
    realized_pnl = db.Column(db.Float, default='0.0')
    side = db.Column(db.String(4))  # 'buy' or 'sell'
    price = db.Column(db.Float)
    amount = db.Column(db.Float)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref=db.backref('trades', lazy=True))



class UserSettings(db.Model):
    __tablename__ = 'user_settings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True)
    take_profit_percentage = db.Column(db.Float, default='3.0', nullable = False)
    take_profit_percentage2 = db.Column(db.Float, default='5.0', nullable = True)
    tp1_close_amount = db.Column(db.Float, default='50.0', nullable = True)
    tp2_close_amount = db.Column(db.Float, default='50.0', nullable = True)
    stop_loss_percentage = db.Column(db.Float, default='2.0', nullable = False)
    future_wallet_margin_usage_ratio = db.Column(db.Float, default='80.0', nullable = False)
    order_type = db.Column(db.String(10), default='market', nullable = False)
    leverage = db.Column(db.Integer , default='10', nullable= False )
    defined_long_margine_per_trade = db.Column(db.Float,default='8.0', nullable = False)
    defined_short_margine_per_trade = db.Column(db.Float,default='8.0', nullable = False)
    max_concurrent = db.Column(db.Integer, default = '5')
    margin_Mode = db.Column(db.String(10), default='cross')
    tg_chatid = db.Column(db.String(15), nullable=True )
    sl_method = db.Column(db.String(10), default='general')
    trailing_stop_callback_rate = db.Column(db.Numeric(4, 3), nullable=True)

    user = db.relationship("User", back_populates="settings")



class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    message = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.now)
    read = db.Column(db.Boolean, default=False)
    
    user = db.relationship('User', back_populates='notifications')
