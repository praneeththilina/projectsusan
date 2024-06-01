from flask import Blueprint, request, jsonify, current_app
from app.models import User
from trading_bot import execute_trade
import os
from datetime import datetime
from app.utils import flash_and_telegram, save_notification
from app.telegram_bot import send_telegram_message_group

trading_bp = Blueprint('trading', __name__)

# List of allowed IP addresses for TradingView webhook
ALLOWED_IPS = ['52.89.214.238', '34.212.75.30', '54.218.53.128', '52.32.178.7']

@trading_bp.route('/trade_alert', methods=['POST'])
def trade_alert():
        # Check if the request IP is allowed
    # if request.remote_addr not in ALLOWED_IPS:
    #     return jsonify({'error': 'Unauthorized IP address'}), 403

    data = request.json
    if not data:
        return jsonify({"error": "Invalid data"}), 400
    
    passphrase = os.getenv('TRADINGVIEW_PASSPHRASE')
    if data['passphrase'] != passphrase:
            return jsonify({"error": "Invalid passphrase"}), 403
    

    pair = data['pair']
    if pair.endswith('.P'):
        pair = pair[:-2]

    side = data['side'].lower()
    price = float(data['price'])
    quantity = data['quantity']

    if not pair or not side or not passphrase:
        return jsonify({"error": "Missing required fields"}), 400


    users = User.query.filter(
            User.expire_date > datetime.now()
        ).all()


    for user in users:
        _api_key = user._api_key
        _api_secret = user._api_secret
        try:
            if _api_key and _api_secret:
                execute_trade(pair, side, user)

                # # Notify user
                # message = f"Trade executed: {side} {quantity} of {pair} at {price}"
                    
                # flash_and_telegram(user, message, category='success')
                
            else:
                message = f"Trade execution failed. Connect API: {side} {quantity} of {pair} at {price}"
                save_notification(user.id,message)

        except Exception as e:
            current_app.logger.error(f"Error executing trade for user {user.id}: {str(e)}")
            message = f"Trade execution failed. Getting error {str(e)}"
            save_notification(user.id,message)
            # flash_and_telegram(user, f"Error executing trade: {str(e)}", category='error')

    message = f"🚀 SusanBot Detected New Opportunity!! 🚨\n \n💡 New Signal: {pair} {'LONG' if side=='buy' else 'SHORT'} 💡\n \n🔄 Leverage: Isolated 10x\n\n🔢 Entry Price: {price}\n\n🎯 Take Profit: {(price + price*2/100) if side == 'buy' else (price - price*2/100)} (Success rate: 90%)\n\n⚠️ Stop Loss: {(price - price*2/100) if side == 'buy' else (price + price*2/100)} (Change it as your risk management)\n\n\n🌐 Join us at <u><i>https://projectsusan.eu.pythonanywhere.com/</i></u> for top-notch trading tools and auto-trading-ready signals!"       
    send_telegram_message_group(message)

    return jsonify({"success": True}), 200

def register_blueprint(app):
    app.register_blueprint(trading_bp)
