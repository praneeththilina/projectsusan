import ccxt
from .telegram_bot import send_telegram_message
from flask import flash 
from .models import Notification
from . import db

def get_ccxt_instance(api_key, api_secret):
    exchange = ccxt.binance({
        'apiKey': api_key,
        'secret': api_secret,
        'enableRateLimit': True,
        'options': {
            'defaultType': 'future',
            'adjustForTimeDifference': True,
        },
    })
    exchange.set_sandbox_mode(True)  # Set to True for testing
    return exchange

# def flash_and_telegram(user, message, category):
#     flash(message, category)
#     if user.settings.tg_chatid:
#         send_telegram_message(user.settings.tg_chatid, message)

def flash_and_telegram(user, message, category='message'):
    flash(message, category)
    if user.settings and user.settings.tg_chatid:
        send_telegram_message(user.settings.tg_chatid, message)

def save_notification(user_id, message):
        notification = Notification(user_id=user_id, message=message) # type: ignore
        db.session.add(notification)
        db.session.commit()