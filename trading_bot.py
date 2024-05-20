from datetime import datetime
from app import db
from app.models import Trade
from app.utils import get_ccxt_instance

def execute_trade(pair, side, amount, api_key, api_secret, user_id):
    try:
        exchange = get_ccxt_instance(api_key, api_secret)
        exchange.load_markets()

        order = None
        if side == 'buy':
            order = exchange.create_market_buy_order(pair, amount)
        elif side == 'sell':
            order = exchange.create_market_sell_order(pair, amount)

        if order:
            trade = Trade(
                timestamp=datetime.now(),
                pair=pair,
                side=side,
                price=order['price'],
                amount=amount,
                user_id=user_id
            ) # type: ignore
            db.session.add(trade)
            db.session.commit()
            print(f"Executed {side} order for {amount} {pair} at {order['price']}")
    except Exception as e:
        print(f"An error occurred: {e}")
