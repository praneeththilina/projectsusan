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
    premium_plan_id = db.Column(db.Integer, db.ForeignKey('premium_plan.id'))
    premium_plan = db.relationship('PremiumPlan', backref='users')
    expire_date = db.Column(db.DateTime)
    premium_request_id = db.Column(db.Integer)
    settings = db.relationship("UserSettings", uselist=False, back_populates="user")
    notifications = db.relationship('Notification', back_populates='user', cascade="all, delete-orphan")
    avatar = db.Column(db.String(50), default='avatar1.svg')

    def is_premium(self):
        return self.expire_date and self.expire_date > datetime.now()


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
        
class PremiumPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    valid_days = db.Column(db.Integer)

    def __str__(self):
        return self.name

class PremiumRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref='requests')
    plan_id = db.Column(db.Integer, db.ForeignKey('premium_plan.id'))
    plan = db.relationship('PremiumPlan', backref='requests')
    created_at = db.Column(db.DateTime, default=datetime.now)
    approved = db.Column(db.Boolean, default=False)
    approved_at = db.Column(db.DateTime, nullable=True)
    rejected = db.Column(db.Boolean, default=False)
    rejected_at = db.Column(db.DateTime, nullable=True)

    def __str__(self):
        return f"Request by {self.user.username} for {self.plan.name}"


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
    status = db.Column(db.String(10))
    realized_pnl = db.Column(db.Integer)
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
    order_type = db.Column(db.String, default='market', nullable = False)
    leverage = db.Column(db.Integer , default='10', nullable= False )
    defined_margine_per_trade = db.Column(db.Float,default='10.0', nullable = False)
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
