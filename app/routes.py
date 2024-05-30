import os
from pytz import timezone
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
from .utils import flash_and_telegram, save_notification, telegram, convert_utc_to_local
from . import db

main = Blueprint('main', __name__)
# limiter = Limiter('main',default_limits=["200 per day", "50 per hour"])  
# limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])

# Load the passphrase from environment variables
TRADINGVIEW_PASSPHRASE = os.getenv('TRADINGVIEW_PASSPHRASE')

# List of allowed IP addresses for TradingView webhook
ALLOWED_IPS = ['52.89.214.238', '34.212.75.30', '54.218.53.128', '52.32.178.7']

# @main.route('/')
# def index():
#     if current_user.is_authenticated:
#         return redirect(url_for('main.dashboard'))
#     return redirect(url_for('security.login'))


@main.route('/')
def index():
    return render_template('landing.html')

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
                                order_type='market',
                                defined_long_margine_per_trade='5',
                                defined_short_margine_per_trade='5',
                                max_concurrent = '5',
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
        order = execute_trade(pair=form.pair.data, side=form.side.data, user=current_user)
  
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
            telegram(current_user, f'🚨 <b>API credentials receintly updated!</b> \n\nHey {current_user.email}!,  Make sure about these changes by you.')
            flash('API credentials receintly updated!', 'success')
            return redirect(url_for('main.dashboard'))
        except Exception as e:
            flash(f'Invalid API credentials: {e}', 'error')
            telegram(current_user, f'🚨 <b>Invalid API credentials!</b> \n\nHey {current_user.email}!,  Are you trying to <b><u>add|change</u></b> API keys in your account? <b>I think it is not a valid one. 🤦‍♀️</b> \n<u>Try again</u>. Here is error data \n{str(e)}')

    
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
            if user._api_key and user._api_secret:
                # Execute trade for each user
                execute_trade(pair=form.pair.data, side=form.side.data, user=user)
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
        telegram(user, message)
        flash('Approved', 'success')
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
                    settings = UserSettings(user_id=current_user.id)  # type: ignore
                    db.session.add(settings)

                settings.take_profit_percentage = form.take_profit_percentage.data
                settings.stop_loss_percentage = form.stop_loss_percentage.data
                settings.leverage = form.leverage.data
                settings.order_type = form.order_type.data
                settings.defined_long_margine_per_trade = form.defined_long_margine_per_trade.data
                settings.defined_short_margine_per_trade = form.defined_short_margine_per_trade.data
                settings.max_concurrent = form.concorrent.data
                settings.tg_chatid = form.tg_chatid.data
                current_user.timezone = form.timezone.data
                db.session.commit()

                message = (f"🚨<b>Your settings have changed!</b>\n\n Here are the new settings \n📌 TP Ratio : {settings.take_profit_percentage} %\n"
                           f"📌 SL Ratio : {settings.stop_loss_percentage} %\n📌 Allowed Margin for Long trade ( $ ) : {settings.defined_long_margine_per_trade} $ \n📌 Allowed Margin for Short trade ( $ ) : {settings.defined_short_margine_per_trade} $\n"
                           f"📌 Fixed Leverage : {settings.leverage}x\n📌 Max Concurrent trades limit: {settings.max_concurrent}  ")
                telegram(current_user, message)
                flash('Settings Changed Successfully!', category='success')

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
        form.leverage.data = current_user.settings.leverage
        form.defined_long_margine_per_trade.data = current_user.settings.defined_long_margine_per_trade
        form.defined_short_margine_per_trade.data = current_user.settings.defined_short_margine_per_trade
        form.concorrent.data = current_user.settings.max_concurrent
        form.tg_chatid.data = current_user.settings.tg_chatid

        if current_user.timezone:
            form.timezone.data = current_user.timezone
        else:
            form.timezone.data = 'Asia/Colombo'  # Preselect Asia/Colombo if no timezone is set
        form.order_type.data = current_user.settings.order_type

    return render_template('settings.html', form=form, formavtar=formavtar)


@main.route('/notifications')
@auth_required('token', 'session')
def notifications():
    form = MarkAsReadForm()
    user_notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    
    
        # Fetch the user's timezone setting (default to UTC if not set)
    user_timezone = timezone(current_user.timezone if current_user.timezone else 'UTC')
    
    # Fetch notifications and convert their timestamps
    user_notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    notifications_data = [
        {
            'id': notification.id,
            'user_id': notification.user_id,
            'message': notification.message,
            'created_at': notification.created_at.astimezone(user_timezone).strftime('%Y-%m-%d %H:%M:%S %Z'),
            'read': notification.read
        } for notification in user_notifications
    ]
    
    return render_template('notifications.html', notifications=notifications_data, form=form)
    # return render_template('notifications.html', notifications=user_notifications, form = form)






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
    

# @main.route('/data/trades')
# def get_trades():
#     trades = Trade.query.filter_by(user_id=current_user.id).all()
#     trade_data = [
#         {
#             'timestamp': trade.timestamp.isoformat(),
#             'pair': trade.pair,
#             'comment': trade.comment,
#             'orderid': trade.orderid,
#             'status': trade.status,
#             'realized_pnl': trade.realized_pnl,
#             'side': trade.side,
#             'price': trade.price,
#             'amount': trade.amount
#         } for trade in trades
#     ]
#     return jsonify(trade_data)


@main.route('/data/trades')
def get_trades():
    # Calculate the date 30 days ago from today
    thirty_days_ago = datetime.now() - timedelta(days=30)
    
    # Query for trades from the last 30 days
    trades = Trade.query.filter(
        Trade.user_id == current_user.id,
        Trade.timestamp >= thirty_days_ago
    ).all()
    
    # Fetch the user's timezone setting (default to UTC if not set)
    user_timezone = timezone(current_user.timezone if current_user.timezone else 'UTC')

    # Prepare the trade data for JSON response
    trade_data = [
        {
            'timestamp': trade.timestamp.astimezone(user_timezone).strftime('%m-%d %H:%M:%S %Z'),
            'pair': trade.pair,
            'comment': trade.comment,
            'orderid': trade.orderid,
            'status': trade.status,
            'realized_pnl': trade.realized_pnl,
            'side': trade.side,
            'price': trade.price,
            'amount': trade.amount
        } for trade in trades
    ]
    # Return the data as JSON
    return jsonify(trade_data)



# Views
@main.route('/confirmed')
def confirmation_success():
    success_message = request.args.get('success')
    email = request.args.get('email')
    identity = request.args.get('identity')
    
    # You can customize this template or message according to your requirements
    return render_template('server_err/confirmation_success.html', success_message=success_message, email=email, identity=identity)

@main.route('/confirm-error')
def confirm_error():
    # You can customize this template or message according to your requirements
    return render_template('server_err/confirmation_error.html')





def register_blueprints(app):
    app.register_blueprint(main)
