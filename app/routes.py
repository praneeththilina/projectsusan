import os
from pytz import timezone
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, jsonify, request
from flask_security.decorators import permissions_accepted, auth_required,\
                    roles_accepted, roles_required
from flask_login import login_required, current_user, logout_user

from .forms import TradeForm, APIForm, SettingsForm, MarkAsReadForm,AvatarSelectionForm, PurchaseFuelForm
from .models import User, UserSettings, Notification, Trade, BotFuelPackage, BotFuelTransaction, IDCounter
from . import limiter, cache
from trading_bot import execute_trade  # Your function to execute trades
from datetime import datetime, timedelta
from app.utils import get_ccxt_instance
from .utils import flash_and_telegram, save_notification, telegram, convert_utc_to_local
from . import db
from collections import OrderedDict

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

@main.route('/purchase_fuel', methods=['GET', 'POST'])
@auth_required('token', 'session')
def purchase_fuel():
    form = PurchaseFuelForm()
    if form.validate_on_submit():
        package = BotFuelPackage.query.get(form.package.data)
        if package:
            transaction = BotFuelTransaction(
                user=current_user,
                package=package,
                payment_method=form.payment_method.data,
                pay_id=form.pay_id.data
            ) # type: ignore
            db.session.add(transaction)
            # current_user.fuel_balance += package.amount
        db.session.commit()
        flash('Fuel purchase successful. Your fuel balance has been updated.', 'success')
        return redirect(url_for('main.dashboard'))
    return render_template('purchase_fuel.html', form=form)

@main.route('/check_fuel')
@auth_required('token', 'session')
def check_fuel():
    fuel_balance = current_user.fuel_balance
    return jsonify({"fuel_balance": fuel_balance})

@main.route('/admin/bot_fuel_requests', methods=['GET', 'POST'])
@auth_required('token', 'session')
@roles_accepted('admin')
@permissions_accepted("admin-write")
def admin_bot_fuel_requests():
    transactions = BotFuelTransaction.query.all()
    return render_template('admin_bot_fuel_requests.html', transactions=transactions)

@main.route('/admin/approve_request/<int:transaction_id>', methods=['POST'])
@auth_required('token', 'session')
@roles_accepted('admin')
@permissions_accepted("admin-write")
def approve_request(transaction_id):
    transaction = BotFuelTransaction.query.get(transaction_id)
    if transaction and not transaction.successful:
        transaction.successful = True
        transaction.user.fuel_balance += transaction.package.amount
        db.session.commit()
        flash('Request approved and fuel added to the user account.', 'success')
        msg = f'''
            ✅✨ Bot Fuel Request Approved! ✨✅
            \nHello {transaction.user.email} ,\n
            \nCongratulations! 🎉 Your bot fuel request has been approved! You're all set to fire up those trades with your new fuel. Your current fuel balance is {transaction.user._fuel_balance} Happy trading! 💰📈'''
        
        telegram(transaction.user, msg)
    return redirect(url_for('main.admin_bot_fuel_requests'))

@main.route('/admin/reject_request/<int:transaction_id>', methods=['POST'])
@auth_required('token', 'session')
@roles_accepted('admin')
@permissions_accepted("admin-write")
def reject_request(transaction_id):
    transaction = BotFuelTransaction.query.get(transaction_id)
    if transaction:
        db.session.delete(transaction)
        db.session.commit()
        flash('Request rejected and removed.', 'success')
        msg = f'''
            🛑 Bot Fuel Request Rejected! 🛑
            \nHello ,\n
            \nWe regret to inform you that your request for bot fuel has been rejected. 😔
            \nIf you have any questions or concerns, please feel free to reach out to us.
            \nThank you for your understanding. 🙏'''
        
        telegram(transaction.user, msg)
    return redirect(url_for('main.admin_bot_fuel_requests'))




@main.route('/dashboard')
@auth_required('token', 'session')
@roles_accepted('admin', 'user')
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
                                leverage='10',
                                margin_Mode = 'cross'
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
@roles_accepted('admin', 'user')
def trade():
    form = TradeForm()
    if form.validate_on_submit():
        api_key = current_user.api_key
        api_secret = current_user.api_secret

        if not api_key or not api_secret:
            flash('API credentials not set!', 'danger')
            return redirect(url_for('main.dashboard'))

        with db.session.begin_nested():
            counter = IDCounter.query.first()
            if not counter:
                counter = IDCounter(counter=0)
                db.session.add(counter)
                db.session.flush()  # Ensure the new counter is available
            counter.counter += 1
            trade_id = counter.counter
            db.session.commit()        

        # Execute the trade
        order = execute_trade(pair=form.pair.data, side=form.side.data, user=current_user, trade_id=trade_id)

        flash('Trade executed successfully!', 'success')
        return redirect(url_for('main.dashboard'))
    return render_template('trade.html', form=form)

# @main.route('/api_credentials', methods=['GET', 'POST'])
# @auth_required('token', 'session')
# def api_credentials():
#     form = APIForm()
#     if form.validate_on_submit():
#         api_key = form.api_key.data
#         api_secret = form.api_secret.data
#         exchange = get_ccxt_instance(api_key, api_secret)

#         try:
#             exchange.fetch_balance()  # Verify API credentials
#             current_user.api_key = api_key
#             current_user.api_secret = api_secret
#             db.session.commit()
#             telegram(current_user, f'🚨 <b>API credentials receintly updated!</b> \n\nHey {current_user.email}!,  Make sure about these changes by you.')
#             flash('API credentials receintly updated!', 'success')
#             return redirect(url_for('main.dashboard'))
#         except Exception as e:
#             flash(f'Invalid API credentials: {e}', 'error')
#             telegram(current_user, f'🚨 <b>Invalid API credentials!</b> \n\nHey {current_user.email}!,  Are you trying to <b><u>add|change</u></b> API keys in your account? <b>I think it is not a valid one. 🤦‍♀️</b> \n<u>Try again</u>. Here is error data \n{str(e)}')


#     return render_template('api_credentials.html', form=form)

@main.route('/api_credentials', methods=['GET', 'POST'])
@auth_required('token', 'session')
@roles_accepted('admin', 'user')
def api_credentials():
    # Check if the user has accepted the terms and conditions
    if not current_user.terms_accepted:
        return redirect(url_for('main.accept_terms'))

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
            telegram(current_user, f'🚨 <b>API credentials recently updated!</b> \n\nHey {current_user.email}!,  Make sure about these changes by you.')
            flash('API credentials recently updated!', 'success')
            return redirect(url_for('main.dashboard'))
        except Exception as e:
            flash(f'Invalid API credentials: {e}', 'error')
            telegram(current_user, f'🚨 <b>Invalid API credentials!</b> \n\nHey {current_user.email}!,  Are you trying to <b><u>add|change</u></b> API keys in your account? <b>I think it is not a valid one. 🤦‍♀️</b> \n<u>Try again</u>. Here is error data \n{str(e)}')

    # Call the new route to check the API status
    api_status = check_api_status()
    
    return render_template('api_credentials.html', form=form, api_status=api_status)


@main.route('/check_api_status')
@auth_required('token', 'session')
@roles_accepted('admin', 'user')
@cache.cached(timeout=1800)  # Cache the response for 30 minutes
def check_api_status():
    if not current_user.api_key or not current_user.api_secret:
        return {"status": "not_connected"}

    exchange = get_ccxt_instance(current_user.api_key, current_user.api_secret)
    try:
        exchange.fetch_balance()  # Verify API credentials
        return {"status": "connected"}
    except Exception:
        return {"status": "not_connected"}

@main.route('/accept_terms', methods=['GET', 'POST'])
@auth_required('token', 'session')
@roles_accepted('admin', 'user')
def accept_terms():
    if request.method == 'POST':
        data = request.get_json()
        if data is None:
            return jsonify({'success': False, 'message': 'No JSON data received.'}), 400

        accept = data.get('accept', False)
        if accept:
            current_user.terms_accepted = True
            current_user.terms_accepted_at = datetime.now()
            db.session.commit()
            return jsonify({'success': True})
        else:
            current_user.terms_accepted = False
            current_user.terms_accepted_at = None
            db.session.commit()
            return jsonify({'success': False, 'message': 'Terms must be accepted to use the service.'})
    
    return render_template('terms.html')


@main.route('/bulk_trade', methods=['GET', 'POST'])
@auth_required('token', 'session')
@roles_accepted('admin', 'user')
def bulk_trade():
    form = TradeForm()
    if form.validate_on_submit():
        users = User.query.filter(
            User.expire_date > datetime.now()
        ).all()

        with db.session.begin_nested():
            counter = IDCounter.query.first()
            if not counter:
                counter = IDCounter(counter=0)
                db.session.add(counter)
                db.session.flush()  # Ensure the new counter is available
            counter.counter += 1
            trade_id = counter.counter
            db.session.commit()        

        for user in users:
            if user._api_key and user._api_secret:
                # Execute trade for each user
                execute_trade(pair=form.pair.data, side=form.side.data, user=user, trade_id=trade_id)
                flash('Bulk trade executed successfully!', 'success')
        return redirect(url_for('main.dashboard'))
    return render_template('bulk_trade.html', form=form)

@main.route('/settings', methods=['GET', 'POST'])
@auth_required('token', 'session')
@roles_accepted('admin', 'user')
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
                settings.margin_Mode = form.marginMode.data
                current_user.timezone = form.timezone.data
                settings.sl_method = form.sl_method.data
                settings.trailing_stop_callback_rate = form.trailing_callback_ratio.data
                settings.take_profit_percentage2 = form.trailing_callback_ratio.data
                settings.tp1_close_amount = form.tp1_close_ratio.data
                settings.tp2_close_amount = form.tp2_close_ratio.data

                db.session.commit()

                message = (f"🚨<b>Your settings have changed!</b>\n\n Here are the new settings\n📌 Selected Margin Mode : {settings.margin_Mode.upper()}  \n📌 TP Ratio : {settings.take_profit_percentage} %\n"
                           f"📌 SL Ratio : {settings.stop_loss_percentage} %\n📌 Allowed Margin for Long trade ( $ ) : {settings.defined_long_margine_per_trade} $ \n📌 Allowed Margin for Short trade ( $ ) : {settings.defined_short_margine_per_trade} $\n"
                           f"📌 Fixed Leverage : {settings.leverage}x\n📌 Max Concurrent trades limit: {settings.max_concurrent} %\n📌 SL Method : {settings.sl_method} ")
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
        form.marginMode.data = current_user.settings.margin_Mode

        if current_user.timezone:
            form.timezone.data = current_user.timezone
        else:
            form.timezone.data = 'Asia/Colombo'  # Preselect Asia/Colombo if no timezone is set
        form.order_type.data = current_user.settings.order_type
        form.sl_method.data = current_user.settings.sl_method
        form.trailing_callback_ratio.data = current_user.settings.trailing_stop_callback_rate
        form.take_profit_percentage2.data = current_user.settings.take_profit_percentage2
        form.tp1_close_ratio.data = current_user.settings.tp1_close_amount
        form.tp2_close_ratio.data = current_user.settings.tp2_close_amount



    return render_template('settings.html', form=form, formavtar=formavtar)


@main.route('/notifications')
@auth_required('token', 'session')
@roles_accepted('admin', 'user')
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
@roles_accepted('admin', 'user')
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
@auth_required('token', 'session')
@roles_accepted('admin', 'user')
def get_trades():
    # Calculate the date 30 days ago from today
    thirty_days_ago = datetime.now() - timedelta(days=30)

    # Query for trades from the last 30 days
    trades = Trade.query.filter(
        Trade.user_id == current_user.id,
        Trade.timestamp >= thirty_days_ago
    ).all()

    # Filter Running Trades
    running_trades = [trade for trade in trades if (trade.comment == "TAKE_PROFIT" or trade.comment == "TAKE_PROFI") and trade.status == "open"]
    print(len(running_trades))

    #Filter relevent trades
    relevant_trades = [trade for trade in trades if (trade.comment == "TAKE_PROFIT" or trade.comment == "TAKE_PROFI")]

    winning_trades =  sum(1 for trade in relevant_trades if trade.realized_pnl > 0)
    print((winning_trades))

    # Count winning trades (assuming a positive realized_pnl indicates a win)
    # winning_trades = sum(1 for trade in market_trades if trade.realized_pnl > 0)

    # Calculate win rate
    win_rate = "{:.2f}".format((winning_trades / (len(relevant_trades) - len(running_trades))) * 100 if len(relevant_trades) > 0 else 0)
    print(win_rate)
    # Fetch the user's timezone setting (default to UTC if not set)
    user_timezone = timezone(current_user.timezone if current_user.timezone else 'UTC')

    # Prepare the trade data for JSON response
    trade_data = [
        {
            'timestamp': trade.timestamp.astimezone(user_timezone),#.strftime('%y-%m-%d %H:%M:%S %Z'),
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

        # Additional data to send
    additional_data = {
        'win-rate': win_rate
        # Add more data here if needed
    }
    # Return the data as JSON
    return jsonify({'trades': trade_data, 'additional_data': additional_data})


@main.route('/history', methods=['GET', 'POST'])
@roles_accepted('admin', 'user')
@auth_required('token', 'session')
def history():
    # Calculate the date 90 days ago from today
    ninety_days_ago = datetime.now() - timedelta(days=90)

    # Query for trades from the last 90 days
    trades = Trade.query.filter(
        Trade.user_id == current_user.id,
        Trade.timestamp >= ninety_days_ago
    ).all()

    # Filter Running Trades
    running_trades = [trade for trade in trades if trade.comment in ["TAKE_PROFIT", "TAKE_PROFI"] and trade.status == "open"]

    # Fetch the user's timezone setting (default to UTC if not set)
    user_timezone = timezone(current_user.timezone if current_user.timezone else 'UTC')

    # Prepare the trade data for JSON response
    trade_data = {}
    for trade in trades:
        if trade.trade_id not in trade_data:
            trade_data[trade.trade_id] = {
                'trade_id': trade.trade_id,
                'date': trade.timestamp.astimezone(user_timezone).strftime('%d %b, %Y'),
                'time': trade.timestamp.astimezone(user_timezone).strftime('%I:%M:%S %p').lower(),
                'pair': trade.pair,
                'market': {
                    'comment': '',
                    'orderid': '',
                    'status': '',
                    'realized_pnl': 0.0,
                    'side': '',
                    'price': 0.0,
                    'amount': 0.0
                },
                'take_profit': None,
                'stop_market': None
            }

        if trade.comment == "MARKET":
            trade_data[trade.trade_id]['market'] = {
                'comment': trade.comment,
                'orderid': trade.orderid,
                'status': trade.status,
                'realized_pnl': trade.realized_pnl,
                'side': trade.side,
                'price': trade.price,
                'amount': trade.amount
            }
        elif trade.comment == "TAKE_PROFIT":
            trade_data[trade.trade_id]['take_profit'] = {
                'comment': trade.comment,
                'orderid': trade.orderid,
                'status': trade.status,
                'realized_pnl': trade.realized_pnl,
                'side': trade.side,
                'price': trade.price,
                'amount': trade.amount
            }
        elif trade.comment == "STOP_MARKET":
            trade_data[trade.trade_id]['stop_market'] = {
                'comment': trade.comment,
                'orderid': trade.orderid,
                'status': trade.status,
                'realized_pnl': trade.realized_pnl,
                'side': trade.side,
                'price': trade.price,
                'amount': trade.amount
            }

    # sorted_trade_data = OrderedDict(sorted(trade_data.items(), key=lambda x: trades[x[0]].timestamp, reverse=True))
    # Return the data as JSON (if needed) or render HTML
    # return jsonify(trade_data)  # Uncomment this line if you want a JSON response
    return render_template('tradedata.html', trade_data=trade_data)



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