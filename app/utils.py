import ccxt
from .telegram_bot import send_telegram_message
from flask import flash , current_app
from .models import Notification, UserSettings, Trade
from . import db
from datetime import datetime

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





def fetch_user_settings(user_id):
    return UserSettings.query.filter_by(user_id=user_id).first()

def fetch_balance(exchange):
    balance = exchange.fetch_balance()
    return balance['total']['USDT']  # Assuming USDT as the base currency

def calculate_trade_amount(total_balance, usage_ratio, rate_per_trade):
    allocated_balance = total_balance * (usage_ratio / 100)
    trade_amount = allocated_balance * (rate_per_trade/100)
    return trade_amount

# def create_stop_market_orders(exchange, pair, side, amount, take_profit_price, stop_loss_price):
#     try:
#         if side == 'buy':
#             tp_order = exchange.create_order(pair, 'STOP_MARKET', 'sell', amount, None, {'stopPrice': take_profit_price})
#             sl_order = exchange.create_order(pair, 'STOP_MARKET', 'sell', amount, None, {'stopPrice': stop_loss_price})
#         elif side == 'sell':
#             tp_order = exchange.create_order(pair, 'STOP_MARKET', 'buy', amount, None, {'stopPrice': take_profit_price})
#             sl_order = exchange.create_order(pair, 'STOP_MARKET', 'buy', amount, None, {'stopPrice': stop_loss_price})
#         return tp_order, sl_order
#     except Exception as e:
#         print(f"An error occurred while creating stop-market orders: {e}")
#         return None, None


def flash_and_telegram(user, message, category='message'):
    flash(message, category)
    if user.settings and user.settings.tg_chatid:
        send_telegram_message(user.settings.tg_chatid, message)

def telegram(user, message):
    if user.settings and user.settings.tg_chatid:
        send_telegram_message(user.settings.tg_chatid, message)


def save_notification(user_id, message):
        notification = Notification(user_id=user_id, message=message) # type: ignore
        db.session.add(notification)
        db.session.commit()
    
def save_trade(user_id, order_data, message, orderid):
        trade = Trade(
            # timestamp=datetime.fromisoformat(order_data['datetime']), # type: ignore
            timestamp=datetime.now(), 
            pair=order_data['info']['symbol'],
            comment = message,
            orderid = orderid,
            status = order_data['status'],
            side =order_data['side'],
            price = (order_data['price'] if order_data['info']['type'] == 'MARKET' else order_data['stopPrice']),
            amount=order_data['amount'],
            user_id=user_id)  # type: ignore
        db.session.add(trade)
        db.session.commit()
    

def save_trade_tpsl(user_id, extracted_order, message, orderid):
        trade = Trade(
            # timestamp=datetime.fromisoformat(order_data['datetime']), # type: ignore
            timestamp=datetime.now(), 
            pair=extracted_order['symbol'],
            comment = message,
            orderid = orderid,
            status = extracted_order['status'],
            side =extracted_order['side'],
            price = extracted_order['stopPrice'],
            amount=extracted_order['quantity'],
            user_id=user_id)  # type: ignore
        db.session.add(trade)
        db.session.commit()
    


    
def fetch_trade_status_for_user(user_id):
    try:
        # Query for open trades for the specified user
        trades = Trade.query.filter(
            Trade.status == 'open' or Trade.status =='NEW',
            Trade.user_id == user_id
        ).all()

        return trades
    except Exception as e:
        current_app.logger.error(f"Error fetching trade status for user {user_id}: {str(e)}")
        return []
    
def fetch_trade_status(exchange, order_id, pair):
    try:

        # Fetch the order details
        order = exchange.fetch_order(order_id, pair)

        # Fetch the trades for the order
        trades = exchange.fetch_my_trades(pair, None, 10, {'orderId': order_id})
        print(trades)

        print(f'trades data: {trades}')
    
        print(f"Order ID to filter: {order_id}")
        print(type(order_id))

        # Filter trades by the given order_id
        filtered_trades = [trade for trade in trades if trade['info']['orderId'] == str(order_id)]

        # Debugging output: Print filtered trades to verify
        print("Filtered Trades:", filtered_trades)

        # Sum the realized PnL for the filtered trades
        total_realized_pnl = sum(float(trade['info']['realizedPnl']) for trade in filtered_trades)
        
        
        print(f'closed total_realized_pnl: {total_realized_pnl}')

        print('--------------------------')
        # print(order2)
        print('--------------------------')
        status = order['status']

        # realized_pnl = order.get('fee', {}).get('cost', 0)  # Assuming 'fee' contains realized PnL info

        return status, total_realized_pnl
    except Exception as e:
        current_app.logger.error(f"Error fetching trade status for order {order_id}: {str(e)}")
        return None, None