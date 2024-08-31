# import os
# from datetime import datetime, timedelta
# import pytz
# import requests
# from app import create_app, db
# from app.models import User, Trade

# # Initialize Flask app
# app = create_app()
# app.app_context().push()

# # Function to send message to Telegram
# def send_telegram_message(chat_id, message):
#     TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
#     send_message_url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
#     payload = {'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'}
#     response = requests.post(send_message_url, data=payload)
#     return response

# # Function to create the daily summary
# def create_daily_summary():
#     users = User.query.all()
#     for user in users:
#         # User's timezone
#         user_timezone = pytz.timezone(user.timezone)
        
#         # Calculate time range for the past day
#         end_time = datetime.now(user_timezone)
#         start_time = end_time - timedelta(days=1)
        
#         # Get trades for the user in the past day
#         trades = Trade.query.filter(
#             Trade.user_id == user.id,
#             Trade.timestamp >= start_time.astimezone(pytz.UTC),
#             Trade.timestamp <= end_time.astimezone(pytz.UTC)
#         ).all()
        
#         # Calculate total PNL and number of trades
#         total_pnl = sum(trade.realized_pnl for trade in trades)
#         # Filter for 'MARKET' comments using list comprehension
#         market_trades = [trade for trade in trades if trade.comment == 'MARKET']

#         total_trades = len(market_trades)
        
#         # Prepare message
#         message = (
#             f"📊 <b>Daily Summary for {user.email}</b> 📊\n"
#             f"🕒 Period: {start_time.strftime('%Y-%m-%d %H:%M:%S')} to {end_time.strftime('%Y-%m-%d %H:%M:%S')} {user.timezone}\n"
#             f"💼 Total PNL: {total_pnl:.2f}\n"
#             f"🔄 Total Trades: {total_trades}\n"
#         )
        
#         # Send message to Telegram
#         chat_id = user.settings.tg_chatid
#         print(chat_id)
#         send_telegram_message(chat_id, message)

# if __name__ == "__main__":
#     create_daily_summary()
import os
from datetime import datetime, timedelta
import pytz
import requests
from app import create_app, db
from app.models import User, Trade

# Initialize Flask app
app = create_app()
app.app_context().push()

# Function to send message to Telegram
def send_telegram_message(chat_id, message):
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    send_message_url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    payload = {'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'}
    response = requests.post(send_message_url, data=payload)
    return response

# Function to send file to Telegram
def send_telegram_file(chat_id, file_path):
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    send_document_url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument'
    if file_path and os.path.exists(file_path):
        with open(file_path, 'rb') as document:
            files = {'document': document}
            response = requests.post(send_document_url, data={'chat_id': chat_id}, files=files)
        return response
    else:
        print(f"File {file_path} does not exist.")
        return None

# Function to create the daily summary
def create_daily_summary():
    users = User.query.all()
    default_timezone = pytz.timezone('UTC')  # Default timezone
    
    for user in users:
        try:
            # Attempt to get user's timezone
            user_timezone = pytz.timezone(user.timezone) if user.timezone else default_timezone
        except pytz.UnknownTimeZoneError:
            # If timezone is invalid, use default timezone
            user_timezone = default_timezone
        
        # Calculate time range for the past day
        end_time = datetime.now(user_timezone)
        start_time = end_time - timedelta(days=1)
        
        # Get trades for the user in the past day
        trades = Trade.query.filter(
            Trade.user_id == user.id,
            Trade.timestamp >= start_time.astimezone(pytz.UTC),
            Trade.timestamp <= end_time.astimezone(pytz.UTC)
        ).all()
        
        # Calculate total PNL and number of trades
        total_pnl = sum(trade.realized_pnl for trade in trades)
        # Filter for 'MARKET' comments using list comprehension
        market_trades = [trade for trade in trades if trade.comment == 'MARKET']
        total_trades = len(market_trades)
        
        # Prepare message
        message = (
            f"📊 <b>Daily Summary for {user.email}</b> 📊\n"
            f"🕒 Period: {start_time.strftime('%Y-%m-%d %H:%M:%S')} to {end_time.strftime('%Y-%m-%d %H:%M:%S')} {user.timezone or 'UTC'}\n"
            f"💼 Total PNL: {total_pnl:.2f}\n"
            f"🔄 Total Trades: {total_trades}\n"
        )
        
        # Send message to Telegram
        chat_id = user.settings.tg_chatid
        send_telegram_message(chat_id, message)
        
        # Send the log file to Telegram
    current_directory = os.path.dirname(os.path.abspath(__file__))
    webhook_log_file_path = os.path.join(current_directory, 'webhook_alerts.log')
    send_telegram_file('5280217227', webhook_log_file_path)

if __name__ == "__main__":
    create_daily_summary()