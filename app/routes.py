import os
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, jsonify
from flask_security.decorators import permissions_accepted, auth_required,\
                    roles_accepted, roles_required
from flask_login import login_required, current_user, logout_user

from .forms import TradeForm, APIForm, RequestPremiumPlanForm, SettingsForm, MarkAsReadForm,AvatarSelectionForm
from .models import User, PremiumPlan, PremiumRequest, UserSettings, Notification, Trade 
from . import limiter
from trading_bot import execute_trade  # Your function to execute trades
from datetime import datetime, timedelta
from app.utils import get_ccxt_instance
from .utils import flash_and_telegram, save_notification
from . import db

main = Blueprint('main', __name__)
# limiter = Limiter('main',default_limits=["200 per day", "50 per hour"])  
# limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])

# Load the passphrase from environment variables
TRADINGVIEW_PASSPHRASE = os.getenv('TRADINGVIEW_PASSPHRASE')

# List of allowed IP addresses for TradingView webhook
ALLOWED_IPS = ['52.89.214.238', '34.212.75.30', '54.218.53.128', '52.32.178.7']

@main.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('security.login'))

@main.route('/dashboard')
@auth_required('token', 'session')
def dashboard():
    trades = Trade.query.filter_by(user_id=current_user.id).all()
    user = current_user
    settings = user.settings

    if not settings:
        settings = UserSettings(user_id=current_user.id,
                                take_profit_percentage='2.0',
                                stop_loss_percentage='2.0',
                                future_wallet_margin_usage_ratio='70.0',
                                future_rate_per_trade='5',
                                leverage='10'
                                )  # type: ignore
        try:
            db.session.add(settings)
            db.session.commit()  # Commit changes to the database
        except Exception as e:
            db.session.rollback()  # Rollback changes if an error occurs
            print(f"Error occurred while adding default settings: {e}")

    return render_template('dashboard.html', trades=trades, user=user)

@main.route('/logout')
@auth_required('token', 'session')
def logout():
    logout_user()
    return redirect(url_for('security.login'))

@main.route('/trade', methods=['GET', 'POST'])
@auth_required('token', 'session')
def trade():
    form = TradeForm()
    if form.validate_on_submit():
        api_key = current_user.api_key
        api_secret = current_user.api_secret

        if not api_key or not api_secret:
            flash('API credentials not set!', 'danger')
            return redirect(url_for('main.dashboard'))

        # Execute the trade
        order = execute_trade(pair=form.pair.data, side=form.side.data, amount=form.amount.data, api_key=api_key, api_secret=api_secret, user_id=current_user.id)
  
        flash('Trade executed successfully!', 'success')
        return redirect(url_for('main.dashboard'))
    return render_template('trade.html', form=form)

@main.route('/api_credentials', methods=['GET', 'POST'])
@auth_required('token', 'session')
def api_credentials():
    form = APIForm()
    if form.validate_on_submit():
        api_key = form.api_key.data
        api_secret = form.api_secret.data
        exchange = get_ccxt_instance(api_key, api_secret)

        try:
            exchange.fetch_balance()  # Verify API credentials
            current_user.api_key = api_key
            current_user.api_secret = api_secret
            db.session.commit()
            flash_and_telegram(current_user, 'API credentials updated successfully!', 'success')
            return redirect(url_for('main.dashboard'))
        except Exception as e:
            flash(f'Invalid API credentials: {e}', 'error')
    
    return render_template('api_credentials.html', form=form)


@main.route('/bulk_trade', methods=['GET', 'POST'])
@auth_required('token', 'session')
def bulk_trade():
    form = TradeForm()
    if form.validate_on_submit():
        users = User.query.filter(
            User.expire_date > datetime.now()
        ).all()

        for user in users:
            if user.api_key and user.api_secret:
                print(f"api {user.api_key.decode('utf-8')}") 
                print(f"secret {user.api_secret.decode('utf-8')}")
                # Execute trade for each user
                execute_trade(pair=form.pair.data, side=form.side.data, amount=form.amount.data, api_key=user.api_key.decode('utf-8'), api_secret=user.api_secret.decode('utf-8'), user_id=user.id)
                flash('Bulk trade executed successfully!', 'success')
        return redirect(url_for('main.dashboard'))
    return render_template('bulk_trade.html', form=form)


@main.route('/request_premium_plan', methods=['GET', 'POST'])
@auth_required('token', 'session')
@limiter.limit("100 per day", key_func=lambda: current_user.id)
def request_premium_plan():
    plans = PremiumPlan.query.all()
    form = RequestPremiumPlanForm(plans)
    user_requests = PremiumRequest.query.filter_by(user_id=current_user.id).order_by(PremiumRequest.created_at.desc()).limit(5).all()

    if form.validate_on_submit():
        user = current_user
        plan_id = form.plan.data
        existing_request = PremiumRequest.query.filter_by(user_id=user.id, approved=False, rejected=False).first()
        if existing_request:
            flash_and_telegram(user, 'You already have a pending request.', 'warning')
            return redirect(url_for('main.dashboard'))
        request = PremiumRequest(user_id=user.id, plan_id=plan_id) # type: ignore
        db.session.add(request)
        db.session.commit()
        flash_and_telegram(user, 'Premium plan request submitted for review.', 'success')

        return redirect(url_for('main.dashboard'))
    return render_template('request_premium_plan.html', form=form, user_requests=user_requests)


@main.route('/admin/plan_requests')
@auth_required('token', 'session')
@roles_accepted('admin')
@permissions_accepted("admin-write")
def admin_review_plan_requests():
    requests = PremiumRequest.query.filter(
        PremiumRequest.approved == False,
        PremiumRequest.rejected == False
    ).order_by(PremiumRequest.created_at.desc()).all()
    pending_count = PremiumRequest.query.filter(
        PremiumRequest.approved == False,
        PremiumRequest.rejected == False
    ).count()
    return render_template('admin_plan_requests.html', requests=requests, pending_count=pending_count)


@main.route('/admin/approve_plan/<int:request_id>')
@auth_required('token', 'session')
@roles_accepted('admin')
@permissions_accepted("admin-write")
def admin_approve_plan(request_id):
    request = PremiumRequest.query.get(request_id)
    if request:
        user = request.user
        plan = request.plan
        user.premium_plan_id = plan.id
        user.expire_date = datetime.now() + timedelta(days=plan.valid_days)
        user.premium_request_id = request.id
        request.approved = True
        request.approved_at = datetime.now()
        db.session.commit()

        message = f'Your premium plan request has been approved.'
        save_notification(user_id=user.id, message=message)
        flash_and_telegram(user, message, 'success')
    else:
        flash('Invalid request.', 'error')
    return redirect(url_for('main.admin_review_plan_requests'))


@main.route('/admin/reject_plan/<int:request_id>')
@auth_required('token', 'session')
@roles_accepted('admin')
@permissions_accepted("admin-write")
def admin_reject_plan(request_id):
    request = PremiumRequest.query.get(request_id)
    if request:
        user = request.user
        request.rejected = True
        request.rejected_at = datetime.now()
        db.session.commit()
        message = f'Premium plan request has been rejected.'
        save_notification(user_id=user.id, message=message)
        flash_and_telegram(user, message, 'error')

    else:
        flash('Invalid request.')
    return redirect(url_for('main.admin_review_plan_requests'))


@main.route('/settings', methods=['GET', 'POST'])
@auth_required('token', 'session')
def settings():
    form = SettingsForm()
    formavtar = AvatarSelectionForm()

    if request.method == 'POST':
        if 'take_profit_percentage' in request.form:  # Check if the settings form is submitted
            if form.validate_on_submit():
                settings = current_user.settings
                if not settings:
                    settings = UserSettings(user_id=current_user.id) # type: ignore
                    db.session.add(settings)
                settings.take_profit_percentage = form.take_profit_percentage.data
                settings.stop_loss_percentage = form.stop_loss_percentage.data
                settings.future_wallet_margin_usage_ratio = form.future_wallet_margin_usage_ratio.data
                settings.tg_chatid = form.tg_chatid.data
                db.session.commit()
                
                message = 'Settings updated successfully!'
                flash_and_telegram(current_user, message, category='success')

                return redirect(url_for('main.settings'))

        if 'avatar' in request.form:  # Check if the avatar form is submitted
            if formavtar.validate_on_submit():
                current_user.avatar = formavtar.avatar.data
                db.session.commit()
                flash('Avatar updated successfully!', 'success')
                return redirect(url_for('main.settings'))

    if current_user.settings:
        form.take_profit_percentage.data = current_user.settings.take_profit_percentage
        form.stop_loss_percentage.data = current_user.settings.stop_loss_percentage
        form.future_wallet_margin_usage_ratio.data = current_user.settings.future_wallet_margin_usage_ratio
        form.tg_chatid.data = current_user.settings.tg_chatid

    return render_template('settings.html', form=form, formavtar=formavtar)

@main.route('/notifications')
@auth_required('token', 'session')
def notifications():
    form = MarkAsReadForm()
    user_notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return render_template('notifications.html', notifications=user_notifications, form = form)

@main.route('/mark_as_read/<int:notification_id>', methods=['POST'])
@auth_required('token', 'session')
def mark_as_read(notification_id):
    form = MarkAsReadForm()
    if form.validate_on_submit():
        notification = Notification.query.get(notification_id)
        if notification and notification.user_id == current_user.id:
            notification.read = True
            db.session.commit()
            flash('Notification marked as read.', 'success')
        else:
            flash('Invalid notification.', 'error')
    else:
        flash('Form validation failed.', 'error')
    return redirect(url_for('main.notifications'))
    

@main.route('/webhook', methods=['POST'])
def webhook():
    # # Check if the request IP is allowed
    # if request.remote_addr not in ALLOWED_IPS:
    #     return jsonify({'error': 'Unauthorized IP address'}), 403

    data = request.json
    if data:
        passphrase = os.getenv('TRADINGVIEW_PASSPHRASE')

        if data['passphrase'] != passphrase:
            return jsonify({"error": "Invalid passphrase"}), 403

        symbol = data['symbol']
        if symbol.endswith('.P'):
            symbol = symbol[:-2]

        action = data['action'].lower()
        price = data['price']
        quantity = data['quantity']

        users = User.query.filter(
            User.expire_date > datetime.now()
        ).all()

        for user in users:
            try:
                if api_key and api_secret:
                    api_key = user.api_key.decode('utf-8')
                    api_secret = user.api_secret.decode('utf-8')
                    exchange = get_ccxt_instance(api_key, api_secret)

                    if action == 'buy':
                        execute_trade(pair=symbol, side=action, amount=quantity, api_key=user.api_key.decode('utf-8'), api_secret=user.api_secret.decode('utf-8'), user_id=user.id)
                    elif action == 'sell':
                        execute_trade(pair=symbol, side=action, amount=quantity, api_key=user.api_key.decode('utf-8'), api_secret=user.api_secret.decode('utf-8'), user_id=user.id)
                    else:
                        continue

                    # Notify user
                    message = f"Trade executed: {action} {quantity} of {symbol} at {price}"
                    
                    flash_and_telegram(user, message, category='success')
                
                else:
                    message = f"Trade execution failed. Connect API: {action} {quantity} of {symbol} at {price}"
                    save_notification(user.id,message)

            except Exception as e:
                current_app.logger.error(f"Error executing trade for user {user.id}: {str(e)}")
                flash_and_telegram(user, f"Error executing trade: {str(e)}", category='error')

        return jsonify({"success": True}), 200
    return jsonify({"error": True}), 404


def register_blueprints(app):
    app.register_blueprint(main)
