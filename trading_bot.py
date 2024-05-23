from app import db
from flask import current_app
from app.models import Trade
from app.utils import get_ccxt_instance, fetch_user_settings, fetch_balance, \
                    calculate_trade_amount, save_trade,flash_and_telegram,\
                    fetch_trade_status_for_user, fetch_trade_status

def against_side(side):
        """
        Determine the opposite side of a trade.

        Parameters:
            side (str): The original side of the trade ('buy' or 'sell').

        Returns:
            str: The opposite side of the trade.
        """
        if side == 'buy':
            return 'sell'
        elif side == 'sell':
            return 'buy'
        elif side == 'long':
            return 'sell'
        elif side == 'short':
            return 'buy'
        else:
            raise ValueError("Invalid side provided. Must be 'buy' or 'sell'.")



# def execute_trade(pair, side, user_id, api_key, api_secret, order_type):
def execute_trade(pair, side, user, order_type):

    try:
        api_key = user.api_key.decode('utf-8')
        api_secret = user.api_secret.decode('utf-8')

        exchange = get_ccxt_instance(api_key, api_secret)
        exchange.load_markets()
        market = exchange.market(pair)
        ticker = exchange.fetch_ticker(pair)
        last_price = ticker['last']
        ask_price = ticker['ask']
        bid_price = ticker['bid']

        user_settings = fetch_user_settings(user.id)
        if not user_settings:
            raise Exception("User settings not found")
        
        # my settings---------------------------------------------------------------------
        total_balance = fetch_balance(exchange)
        print(f"total_balance :{total_balance}")
        trade_amount = calculate_trade_amount(total_balance, user_settings.future_wallet_margin_usage_ratio, user_settings.future_rate_per_trade)
        print(f"trade_amount :{trade_amount}")

        saved_leverage = user_settings.leverage
        exchange.set_leverage(saved_leverage, pair)
        print(f"leverage :{exchange.set_leverage(saved_leverage, pair)}")

        exchange.set_margin_mode(marginMode='ISOLATED' , symbol=pair)
        print(f"set_margin_mode :{exchange.set_margin_mode(marginMode='ISOLATED' , symbol=pair)}")

        position_size = (trade_amount * saved_leverage)/last_price
        print(f"position size: {position_size}")
        # end my settings-----------------------------------------------------------------

        # if order_type is 'market', then price is not needed
        price = None
        # if order_type is 'limit', then set a price at your desired level
        if order_type == 'limit':
            price = bid_price * 0.95 if (side == 'buy') else ask_price * 1.05  # i.e. 5% from current price

        stop_loss_trigger_price = (last_price if order_type == 'market' else price) * ((1-(user_settings.stop_loss_percentage/100)) if side == 'buy' else (1+(user_settings.stop_loss_percentage/100)))
        take_profit_trigger_price = (last_price if order_type == 'market' else price) * ((1+(user_settings.take_profit_percentage/100)) if side == 'buy' else (1-(user_settings.take_profit_percentage/100)))

        params = {
            'marginMode' : 'isolated',
        }
        position_amount = market['contractSize'] * position_size
        position_value = position_amount * last_price

        # log
        print('Going to open a position', 'for', position_size, 'contracts worth', position_amount, market['base'], '~', position_value, market['settle'], 'using', side, order_type, 'order (', (exchange.price_to_precision(pair, price) if order_type == 'limit' else ''), '), using the following params:')
        print('User leverage', saved_leverage, 'x using for this trade. tp ratio: ' , user_settings.take_profit_percentage/100, 'and SL ratio :' , user_settings.stop_loss_percentage/100, 'using for it. ' )
        print(params)

        print('-----------------------------------------------------------------------')
        print('---------------------Executing trade--------------------------------------------------')

            # order = exchange.create_order(symbol, 'market', action.lower(), quantity, params=param_market_order)
        positions_risk = {}
        mySymbol = [pair,]
        positions_risk = exchange.fetch_positions_risk(mySymbol)   
        myrisk = [position for position in positions_risk if float(position['contracts']) > 0]


        # Return only required fields
        positions = []
        for position in myrisk:
            positions.append({'symbol': position['info']['symbol'],
                                'contracts': position['contracts'],
                                'side': position['side']})
                
        print("Running Postions:", positions)

        try:
            # make orders None before forword
            created_order = None
            order_stopLoss = None
            order_TP = None

                    # calcell running positions.
            if positions :
                close_running_position = exchange.create_order(pair, 'market', against_side(position['side']), amount=position['contracts'], params={ 'reduceOnly': True})
                cancel_all_limit_orders = exchange.cancel_all_orders(symbol=pair)
            # ------------------------------
            created_order = exchange.create_order(pair, order_type, side, position_amount, price, params)
            order_stopLoss = exchange.create_order(pair, 'market', against_side(side.lower()), amount=position_amount, params={'stopLossPrice': stop_loss_trigger_price ,'reduceOnly': True, 'marginMode' : 'isolated'})
            order_TP = exchange.create_order(pair, 'market', against_side(side.lower()), amount=position_amount, params={'takeProfitPrice': take_profit_trigger_price ,'reduceOnly': True, 'marginMode' : 'isolated'})
            

            print('Created an order', created_order)
            print('-----------------------------------------------------------------------')
            print('Created sl tp order', order_stopLoss)  
            print('-----------------------------------------------------------------------')
            print('Created sl tp order', order_TP)     
            # # Fetch all your open orders for this symbol
            # # - use 'fetchOpenOrders' or 'fetchOrders' and filter with 'open' status
            # # - note, that some exchanges might return one order object with embedded stoploss/takeprofit fields, while other exchanges might have separate stoploss/takeprofit order objects
            # all_open_orders = exchange.fetch_open_orders(pair)
            # print('Fetched all your orders for this symbol', all_open_orders)

            if close_running_position:
                message = 'FORCE_CLOSED'
                orderid = close_running_position['info']['orderId']
                save_trade(user.id, close_running_position, message, orderid)

            if created_order:
                message = created_order['info']['type']
                orderid = created_order['info']['orderId']
                save_trade(user.id, created_order, message, orderid)

            if order_stopLoss:
                message = order_stopLoss['info']['type']
                orderid = order_stopLoss['info']['orderId']
                save_trade(user.id, order_stopLoss,message, orderid)

            if order_TP:
                message = order_TP['info']['type']
                orderid = order_TP['info']['orderId']
                save_trade(user.id, order_TP,message, orderid)

            #  alert sent--------- 
            if created_order and order_stopLoss and order_TP:
                
                message = f"---------------------\nNew trade executed!\n {side} {'{:.4f}'.format(position_amount)} of {pair} \n|    Entry at {created_order['price']} \n|    TP at {order_TP['stopPrice']} \n|    SL at {order_stopLoss['stopPrice']} \n---------------------"
                flash_and_telegram(user, message, category='success')

            # Update databse 
            try:
                open_trades = fetch_trade_status_for_user(user.id)
                for trade in open_trades:
                    current_status, realized_pnl = fetch_trade_status(exchange, trade.orderid, trade.pair)
                    print(f'current_status: {current_status} and realized_pnl is {realized_pnl}')
                    if (current_status and trade.status != 'open')  or (current_status and current_status != trade.status):
                        trade.status = current_status
                        trade.realized_pnl = realized_pnl
                        db.session.commit()
                        print(f"Updated trade {trade.orderid}: status={current_status}, realized_pnl={realized_pnl}")

            except Exception as e:
                current_app.logger.error(f"Error verifying open trades for user {user.id}: {str(e)}")

        except Exception as e:
            print(str(e))

        print('---------------------Execution End--------------------------------------------------')

    except Exception as e:
        print(f"An error occurred: {e}")