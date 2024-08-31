import logging
from flask import Blueprint, request, jsonify, current_app
from flask_security.decorators import auth_required
from sqlalchemy.exc import NoResultFound
from flask_login import current_user
from app.models import db, WebhookURL, User, Subscription, IDCounter
from app.telegram_bot import send_telegram_message_group  # Assume this is a utility function for sending messages
from trading_bot import execute_trade
import requests
from app.utils import save_notification

# Set up a dedicated logger for webhook alerts
webhook_logger = logging.getLogger('webhook_alerts')
webhook_logger.setLevel(logging.INFO)
file_handler = logging.FileHandler('webhook_alerts.log')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(formatter)
webhook_logger.addHandler(file_handler)

webhook_alert_bp = Blueprint('webhook_alert_bp', __name__)

# Route to receive webhook alerts
@webhook_alert_bp.route('/webhook/<webhook_url>', methods=['POST'])
def receive_alert(webhook_url):
    webhook_logger.info(f"Received alert for webhook URL: {webhook_url}")
    
    # Validate the webhook URL
    webhook = WebhookURL.query.filter_by(url=webhook_url).first()
    if not webhook:
        webhook_logger.warning(f"Invalid webhook URL: {webhook_url}")
        return jsonify({"error": "Invalid webhook URL"}), 403

    data = request.json
    if not data:
        webhook_logger.warning(f"Invalid data received for webhook URL: {webhook_url}")
        return jsonify({"error": "Invalid data"}), 400

    pair = data.get('pair')
    if pair and pair.endswith('.P'):
        pair = pair[:-2]

    side = data.get('side', '').lower()
    price = data.get('price')
    quantity = data.get('quantity')

    if not pair or not side or price is None or quantity is None:
        webhook_logger.warning(f"Missing required fields in data for webhook URL: {webhook_url}")
        return jsonify({"error": "Missing required fields"}), 400

    # Ensure data types are correct
    try:
        price = float(price)
        quantity = float(quantity)
    except ValueError:
        webhook_logger.error(f"Invalid data types for webhook URL: {webhook_url}")
        return jsonify({"error": "Invalid data types"}), 400

    user = User.query.get(webhook.user_id)
    if not user:
        webhook_logger.error(f"User not found for webhook URL: {webhook_url}")
        return jsonify({"error": "User not found"}), 404

    if not user._fuel_balance > 10:
        webhook_logger.error(f"User {user.id} has insufficient fuel balance.")
        raise Exception("Fuel Not Enough!")

    with db.session.begin_nested():
        counter = IDCounter.query.first()
        if not counter:
            counter = IDCounter(counter=0)
            db.session.add(counter)
            db.session.flush()  # Ensure the new counter is available
        counter.counter += 1
        trade_id = counter.counter
        db.session.commit()

    webhook_logger.info(f"Alert Data: {side} : {quantity}  {pair} at {price}")


    # Execute trade for the user
    try:
        if user._api_key and user._api_secret:
            execute_trade(pair, side, user, trade_id=trade_id, quantity_tv=quantity )
            message = f"Trade executed: {side} {quantity} of {pair} at {price}"
            # webhook_logger.info(message)
            send_telegram_message_group(message)
        else:
            message = f"Trade execution failed. Connect API: {side} {quantity} of {pair} at {price}"
            webhook_logger.warning(message)
            save_notification(user.id, message)
    except Exception as e:
        webhook_logger.error(f"Error executing trade for user {user.id}: {str(e)}")

    # Send signal to followers
    notify_followers(user, data)

    return jsonify({"success": True}), 200

def notify_followers(user, signal_data):
    subscriptions = Subscription.query.filter_by(premium_user_id=user.id).all()
    for subscription in subscriptions:
        follower = subscription.follower
        if follower.webhook_url:
            try:
                requests.post(follower.webhook_url.url, json=signal_data)
                webhook_logger.info(f"Sent signal to follower {follower.email}")
            except requests.RequestException as e:
                webhook_logger.error(f"Error sending signal to {follower.email}: {e}")

def register_blueprint(app):
    app.register_blueprint(webhook_alert_bp)
