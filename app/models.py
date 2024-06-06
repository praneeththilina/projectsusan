from flask_security.core import UserMixin, RoleMixin
from flask_security.datastore import AsaList
from sqlalchemy.ext.mutable import MutableList
from . import db
import uuid
from datetime import datetime
from .crypto_utils import encrypt, decrypt
from flask_security.models import fsqla_v3 as fsqla


fsqla.FsModels.set_db_info(db)

class Role(db.Model, fsqla.FsRoleMixin):
    pass

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

class Trade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
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
    take_profit_percentage = db.Column(db.Float, default='2.0', nullable = False)
    stop_loss_percentage = db.Column(db.Float, default='2.0', nullable = False)
    future_wallet_margin_usage_ratio = db.Column(db.Float, default='80.0', nullable = False)
    order_type = db.Column(db.String(10), default='market', nullable = False)
    leverage = db.Column(db.Integer , default='10', nullable= False )
    defined_long_margine_per_trade = db.Column(db.Float,default='8.0', nullable = False)
    defined_short_margine_per_trade = db.Column(db.Float,default='8.0', nullable = False)
    max_concurrent = db.Column(db.Integer, default = '5')
    margin_Mode = db.Column(db.String(10), default='cross')
    tg_chatid = db.Column(db.String(15), nullable=True )
    user = db.relationship("User", back_populates="settings")



class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    message = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.now)
    read = db.Column(db.Boolean, default=False)
    
    user = db.relationship('User', back_populates='notifications')
