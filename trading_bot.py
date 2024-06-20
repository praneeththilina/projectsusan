from app import db
from flask import current_app
from datetime import datetime
from pprint import pprint
from app.models import Trade
from app.utils import get_ccxt_instance, fetch_user_settings, fetch_balance, \
                    calculate_trade_amount, save_trade,flash_and_telegram, telegram,\
                    fetch_trade_status_for_user, fetch_trade_status, save_trade_tpsl

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




def place_order(exchange, pair, order_type, side, position_amount, price, stop_loss_trigger_price, take_profit_trigger_price1, take_profit_trigger_price2, tp_1_close_ratio, tp_2_close_ratio,tp_2_profit_ratio,positionSide, sl_method, trailing_stop_callback_rate, decimal_places):
    orders = []
    print(f'tp trigger price: {take_profit_trigger_price1} , sl triger price: {stop_loss_trigger_price}')
    Trailing_activation_price =str(round(take_profit_trigger_price1,decimal_places))
    print(Trailing_activation_price)
    # Limit order
    limit_order = {
        'symbol': pair,
        'type': order_type,
        'side': side,
        'amount': position_amount,
        'price': price,
        'params': {
            'positionSide': positionSide
        }
    }
    orders.append(limit_order)

    if sl_method == 'general':
        # Stop-loss order (general method)
        stop_loss_order = {
            'symbol': pair,
            'type': 'STOP_MARKET',
            'side': against_side(side),
            'price': stop_loss_trigger_price,
            'amount': position_amount,
            'params': {
                'stopPrice': stop_loss_trigger_price,
                'positionSide': positionSide,
                'timeInForce': 'GTE_GTC',
                'workingType': 'CONTRACT_PRICE'
            }
        }
        orders.append(stop_loss_order)

    elif sl_method == 'trailing':
        # Trailing stop order
        trailing_stop_order = {
            'symbol': pair,
            'type': 'TRAILING_STOP_MARKET',
            'side': against_side(side),
            'price': price,
            'amount': position_amount,
            'params': {
                'activationprice' : Trailing_activation_price,
                'trailingPercent': trailing_stop_callback_rate,
                'positionSide': positionSide,
                'timeInForce': 'GTE_GTC'
            }
        }
        orders.append(trailing_stop_order)

        stop_loss_order = {
            'symbol': pair,
            'type': 'STOP_MARKET',
            'side': against_side(side),
            'price': stop_loss_trigger_price,
            'amount': position_amount,
            'params': {
                'stopPrice': stop_loss_trigger_price,
                'positionSide': positionSide,
                'timeInForce': 'GTE_GTC',
                'workingType': 'CONTRACT_PRICE'
            }
        }
        orders.append(stop_loss_order)


    if tp_2_profit_ratio > 0:
        # Take-profit order1
        take_profit_order1 = {
            'symbol': pair,
            'type': 'TAKE_PROFIT',
            'side': against_side(side),
            'price': take_profit_trigger_price1,
            'amount': (position_amount * tp_1_close_ratio)/100,
            'params': {
                'stopPrice': take_profit_trigger_price1,
                'positionSide': positionSide,
                'timeInForce': 'GTE_GTC',
                'workingType': 'CONTRACT_PRICE'
            }
        }
        orders.append(take_profit_order1)

    # Take-profit order2
        take_profit_order2 = {
            'symbol': pair,
            'type': 'TAKE_PROFIT',
            'side': against_side(side),
            'price': take_profit_trigger_price2,
            'amount': (position_amount * tp_2_close_ratio)/100,
            'params': {
                'stopPrice': take_profit_trigger_price2,
                'positionSide': positionSide,
                'timeInForce': 'GTE_GTC',
                'workingType': 'CONTRACT_PRICE'
            }
        }
        orders.append(take_profit_order2)
    
    elif tp_2_profit_ratio == 0 or tp_2_profit_ratio == None:
        # Take-profit order1
        take_profit_order1 = {
            'symbol': pair,
            'type': 'TAKE_PROFIT',
            'side': against_side(side),
            'price': take_profit_trigger_price1,
            'amount': (position_amount * tp_1_close_ratio)/100,
            'params': {
                'stopPrice': take_profit_trigger_price1,
                'positionSide': positionSide,
                'timeInForce': 'GTE_GTC',
                'workingType': 'CONTRACT_PRICE'
            }
        }
        orders.append(take_profit_order1)


    try:
        response = exchange.create_orders(orders)
        return response
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


# Function to check if a coin pair is in the positions list
def is_coin_pair_in_positions(positions, coin_pair):
    for position in positions:
        # if position['symbol'] == coin_pair:
        if position.get('symbol') == coin_pair:
            return True
    return False

def count_decimal_places(min_price):
    min_price = str(min_price)
    if '.' in str(min_price):
        integer_part, fractional_part = min_price.split('.')
        decimal_places = len(fractional_part) 
        return decimal_places

    else:
        return 1


# def execute_trade(pair, side, user_id, api_key, api_secret, order_type):
def execute_trade(pair, side, user, trade_id):

    try:
        api_key = user.api_key.decode('utf-8')
        api_secret = user.api_secret.decode('utf-8')

        exchange = get_ccxt_instance(api_key, api_secret)
        exchange.load_markets()
        market = exchange.market(pair)
        print(market)

        balance = exchange.fetch_balance()
        # Print the entire balance dictionary to understand its structure
        # pprint(balance)

        # Safely extract positions if they exist
        positions = balance.get('info', {}).get('positions', [])

        # Filter positions where entryPrice is greater than 0.0
        filtered_positions = [position for position in positions if float(position.get('entryPrice', 0.0)) != 0.0]
        running_position_count = len(filtered_positions)

        # Check if the coin pair is in the positions list
        if is_coin_pair_in_positions(filtered_positions, pair):
            print(f'Trade can override for {pair}')
        else:
            print(f'{pair} is not in the positions list')


        # Print filtered positions
        # pprint(filtered_positions)
        print(f"\nrunning positions count :{running_position_count}")

        user_settings = fetch_user_settings(user.id)
        if not user_settings:
            raise Exception("User settings not found")
        

        fuel_balance = user._fuel_balance
        if fuel_balance < 10:
            raise Exception('Not enough bot fuel to execute trade.')


        # my settings---------------------------------------------------------------------

        allwed_concurrent_tarde_limit = user_settings.max_concurrent

        if (allwed_concurrent_tarde_limit > running_position_count) or is_coin_pair_in_positions(filtered_positions, pair):   # concorrent trade limit from db
            ticker = exchange.fetch_ticker(pair)
            last_price = ticker['last']
            ask_price = ticker['ask']
            bid_price = ticker['bid']

            min_price = market['limits']['price']['min'] #minimum usdt value need the position value
            min_cost = market['limits']['cost']['min'] #minimum usdt value need the position cost
            persition = market['precision']['price']
            min_amount = market['limits']['amount']['min']
            
            decimal_places = count_decimal_places(min_price)



            # min_price = float(min_price + 0.1) if float(min_price + 0.1) > float(min_cost + 0.1) else float(min_cost + 0.1) # nomrmalized minimum cost to fix errors
            x = (min_amount * last_price)
            min_price = x if (x > min_price + persition) else ((min_price + persition) if (min_price+persition > min_cost + persition) else min_cost + persition)


            
            order_type = user_settings.order_type
            margin_mode = user_settings.margin_Mode
            saved_leverage = user_settings.leverage
            long_allowcated_margin = user_settings.defined_long_margine_per_trade 
            short_allowcated_margin = user_settings.defined_short_margine_per_trade
            sl_method = user_settings.sl_method
            trailing_callback_rate = user_settings.trailing_stop_callback_rate
            tp_1_profit_ratio =user_settings.take_profit_percentage 
            tp_2_profit_ratio =user_settings.take_profit_percentage2             
            tp_1_close_ratio = user_settings.tp1_close_amount
            tp_2_close_ratio = user_settings.tp2_close_amount            


            exchange.set_leverage(saved_leverage, pair)
            print(f"leverage :{exchange.set_leverage(saved_leverage, pair)}")

            current_margin_mode =  exchange.set_margin_mode(marginMode=margin_mode , symbol=pair)
            print(f"set_margin_mode :{current_margin_mode}")

            trade_amount =  long_allowcated_margin if side=='buy' else short_allowcated_margin
            calculated_usdt_value = trade_amount * saved_leverage

            position_usdt_value = calculated_usdt_value if calculated_usdt_value >= min_price else min_price

            if calculated_usdt_value < min_price:
                # message = f"🧑‍🔧 Hey maximum margin not enough to execute current trade for {pair}, \nTherefor im going to execute it by <u>minimum value rule</u> from binance. "
                message = f" 🚨💡 <b>{pair} Trade Alert!</b> 💡🚨 \n⚠️ Max margin not enough for the trade. Using Binance's min value rule. 📉🔧\nStay tuned! 📲💸"
                telegram(user, message)

            position_size = position_usdt_value/last_price
            print(f"position size: {position_size}")

            if side == 'buy':
                positionSide = 'LONG'
            elif side == 'sell':
                positionSide = 'SHORT'
            
            else:
                raise ValueError("Invalid side provided. Must be 'buy' or 'sell'.") 
            

            # end my settings-----------------------------------------------------------------

            # if order_type is 'limit', then set a price at your desired level
            if order_type == 'limit' and bid_price and ask_price:
                price = (float(bid_price) * 0.95) if (side == 'buy') else (float(ask_price) * 1.05)  # i.e. 5% from current price

            else:
                price = None

            stop_loss_trigger_price = (last_price if order_type == 'market' else price) * ((1-(user_settings.stop_loss_percentage/100)) if side == 'buy' else (1+(user_settings.stop_loss_percentage/100)))
            take_profit_trigger_price1 = (last_price if order_type == 'market' else price) * ((1+(user_settings.take_profit_percentage/100)) if side == 'buy' else (1-(user_settings.take_profit_percentage/100)))
            take_profit_trigger_price2 = (last_price if order_type == 'market' else price) * ((1+(user_settings.take_profit_percentage2/100)) if side == 'buy' else (1-(user_settings.take_profit_percentage2/100)))
            params = {
                'marginMode' : margin_mode,
                'positionSide': positionSide
            }
            position_amount = market['contractSize'] * position_size
            position_value = position_amount * last_price

            # log
            print('Going to open a position', 'for', position_size, 'contracts worth', position_amount, market['base'], '~', position_value, market['settle'], 'using', side, order_type, 'order (', (exchange.price_to_precision(pair, price) if order_type == 'limit' else ''), '), using the following params:')
            print('User leverage', saved_leverage, 'x using for this trade. tp ratio: ' , user_settings.take_profit_percentage/100, 'and SL ratio :' , user_settings.stop_loss_percentage/100, 'using for it. ' )
            print(params)

            print('-----------------------------------------------------------------------')
            print('---------------------Executing trade--------------------------------------------------')

            try:
                # make orders None before forword
                created_order = None
            
                # ------------------------------
                # created_order = exchange.create_order(pair, order_type, side, position_amount, price, params= {'marginMode' : margin_mode,'positionSide': positionSide,})
                order_response = place_order(exchange, pair, order_type, side, position_amount, price, stop_loss_trigger_price, take_profit_trigger_price1, take_profit_trigger_price2, tp_1_close_ratio, tp_2_close_ratio ,tp_2_profit_ratio, positionSide, sl_method, trailing_stop_callback_rate=trailing_callback_rate, decimal_places= decimal_places)
                print(f"created order : {created_order}")
                print(f"tp sl: {order_response}")
                
                # Extract relevant details
                extracted_orders = []
                if order_response:
                    for order in order_response:
                        order_info = order['info']
                        extracted_order = {
                            'orderId': order_info['orderId'],
                            'origType': order_info['origType'],
                            'symbol': order_info['symbol'],
                            'price': order_info['price'],
                            'stopPrice': order_info['stopPrice'],
                            'quantity': order_info['origQty'],
                            'status' : order_info['status'],
                            'side' : order_info['side'],
                            'avgPrice' : order_info['avgPrice']
                        }
                        extracted_orders.append(extracted_order)

                    # Print extracted details
                    for extracted_order in extracted_orders:
                        print(f"Order ID: {extracted_order['orderId']}")
                        print(f"Original Type: {extracted_order['origType']}")
                        print(f"Symbol: {extracted_order['symbol']}")
                        print(f"Price: {extracted_order['price']}")
                        print(f"Stop Price: {extracted_order['stopPrice']}")
                        print(f"Quantity: {extracted_order['quantity']}")
                        print(f"status: {extracted_order['status']}")
                        print(f"side: {extracted_order['side']}")
                        print(f"avgPrice: {extracted_order['avgPrice']}")

                        message = extracted_order['origType']
                        orderid = extracted_order['orderId']

                        # Deduct fuel and execute trade
                        user.fuel_balance -= 10
                        db.session.commit()
                        save_trade_tpsl(user.id, extracted_order, message, orderid, trade_id)
                        if message == 'MARKET':
                            tg_alert = f"─── ⋆⋅☆⋅⋆ ──\n<b><u>New trade executed!</u></b>\n {extracted_order['side']} {'{:.4f}'.format(float(extracted_order['quantity']))} of {extracted_order['symbol']} \n🎲    Entry at {'{:.4f}'.format(float(extracted_order['avgPrice']))} \n🐳    TP1 at {'{:.4f}'.format(take_profit_trigger_price1)} \n🐳    TP2 at {'{:.4f}'.format(take_profit_trigger_price2)} \n🐡    SL at {'{:.4f}'.format(stop_loss_trigger_price)} \n─── ⋆⋅☆⋅⋆ ──"
                            telegram(user, tg_alert)

                        print("\n")

                # if created_order:
                #     message = created_order['info']['type']
                #     orderid = created_order['info']['orderId']
                #     # Deduct fuel and execute trade
                #     user.fuel_balance -= 10
                #     db.session.commit()
                #     save_trade(user.id, created_order, message, orderid)

                # #  alert sent--------- 
                # if created_order:               
                #     message = f"─── ⋆⋅☆⋅⋆ ──\n<b><u>New trade executed!</u></b>\n {side} {'{:.4f}'.format(position_amount)} of {pair} \n🎲    Entry at {'{:.4f}'.format(created_order['price'])} \n🐳    TP at {'{:.4f}'.format(take_profit_trigger_price)} \n🐡    SL at {'{:.4f}'.format(stop_loss_trigger_price)} \n─── ⋆⋅☆⋅⋆ ──"
                #     telegram(user, message)

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
                    message = f"🚧 Hey {user.email}!\nGot an error while verifing your trade history. "
                    telegram(user, message)

            except Exception as e:
                print(str(e))
                message = f"🚧 Hey {user.email}!\nGot an error while trying to execute trade. {str(e)} . Please visit User guide page to fix it. "
                telegram(user, message)

            print('---------------------Execution End--------------------------------------------------')

        else:
            raise Exception('Max allawed concurrent trade limit cannot exceed!. If you want to override, see settings tab.')



    except Exception as e:
        print(f"An error occurred: {e}")
        message = f"🚧 Hey {user.email}! \nGot an error while trying to execute trade. {str(e)} . Please visit User guide page to fix it. "
        telegram(user, message)
