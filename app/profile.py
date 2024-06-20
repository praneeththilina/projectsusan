from flask import Blueprint, render_template, abort, redirect, url_for, flash
from flask_login import current_user
from flask_security.decorators import auth_required, roles_accepted
from app.models import db, User, Subscription, PremiumPackage
from datetime import datetime

profile_bp = Blueprint('profile_bp', __name__)

@profile_bp.route('/profile/<int:user_id>')
@auth_required('token', 'session')
@roles_accepted('admin', 'user')
def profile(user_id):
    user = User.query.get(user_id)
    if not user:
        abort(404)  # User not found
    
    # Additional data for the profile template
    additional_data = {
        'subscriptions': user.following,
        'followers': user.followers,
        'webhook_url': user.webhook_url.url if user.webhook_url else None
    }
    
    # Determine premium status
    premium_status = {
        'is_premium': user.is_premium,
        'expiry_date': user.expire_date if user.is_premium else None
    }
    
    return render_template('users/profile.html', user=user, additional_data=additional_data, premium_status=premium_status)

@profile_bp.route('/profile/follow/<int:user_id>', methods=['POST'])
@auth_required('token', 'session')
@roles_accepted('admin', 'user')
def follow_user(user_id):
    if current_user.id == user_id:
        flash("You cannot follow yourself.")
        return redirect(url_for('profile_bp.profile', user_id=user_id))
    
    user_to_follow = User.query.get(user_id)
    if not user_to_follow:
        abort(404)  # User not found
    
    subscription = Subscription.query.filter_by(follower_id=current_user.id, premium_user_id=user_id).first()
    if subscription:
        flash("You are already following this user.")
    else:
        new_subscription = Subscription(follower_id=current_user.id, premium_user_id=user_id)
        db.session.add(new_subscription)
        db.session.commit()
        flash(f"You are now following {user_to_follow.username}.")
    
    return redirect(url_for('profile_bp.profile', user_id=user_id))

@profile_bp.route('/profile/unfollow/<int:user_id>', methods=['POST'])
@auth_required('token', 'session')
@roles_accepted('admin', 'user')
def unfollow_user(user_id):
    if current_user.id == user_id:
        flash("You cannot unfollow yourself.")
        return redirect(url_for('profile_bp.profile', user_id=user_id))
    
    user_to_unfollow = User.query.get(user_id)
    if not user_to_unfollow:
        abort(404)  # User not found
    
    subscription = Subscription.query.filter_by(follower_id=current_user.id, premium_user_id=user_id).first()
    if subscription:
        db.session.delete(subscription)
        db.session.commit()
        flash(f"You have unfollowed {user_to_unfollow.username}.")
    else:
        flash("You are not following this user.")
    
    return redirect(url_for('profile_bp.profile', user_id=user_id))


def register_blueprint(app):
    app.register_blueprint(profile_bp)