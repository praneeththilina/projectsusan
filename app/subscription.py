from flask import Blueprint, request, jsonify
from flask_login import current_user
from app.models import db, User, Subscription
import datetime
from flask_security.decorators import permissions_accepted, auth_required, roles_accepted


subscription_bp = Blueprint('subscription_bp', __name__)

@subscription_bp.route('/subscribe/<int:premium_user_id>', methods=['POST'])
@auth_required('token', 'session')
@roles_accepted('admin', 'user')
def subscribe(premium_user_id):
    premium_user = User.query.get(premium_user_id)
    if not premium_user or not premium_user.is_premium:
        return jsonify({"error": "Invalid premium user"}), 400

    if Subscription.query.filter_by(follower_id=current_user.id, premium_user_id=premium_user_id).first():
        return jsonify({"error": "Already subscribed"}), 400

    subscription = Subscription(follower_id=current_user.id, premium_user_id=premium_user_id)
    db.session.add(subscription)
    db.session.commit()

    return jsonify({"message": f"Subscribed to {premium_user.email}"}), 200

@subscription_bp.route('/unsubscribe/<int:premium_user_id>', methods=['POST'])
@auth_required('token', 'session')
@roles_accepted('admin', 'user')
def unsubscribe(premium_user_id):
    subscription = Subscription.query.filter_by(follower_id=current_user.id, premium_user_id=premium_user_id).first()
    if not subscription:
        return jsonify({"error": "Not subscribed"}), 400

    db.session.delete(subscription)
    db.session.commit()

    return jsonify({"message": "Unsubscribed successfully"}), 200

def register_blueprint(app):
    app.register_blueprint(subscription_bp)
