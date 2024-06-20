import ccxt
import pandas as pd
import pandas_ta as ta
import time
from finlab_crypto import backtest

# Initialize Binance futures client
exchange = ccxt.binance({
    'options': {'defaultType': 'future'}
})

# Function to fetch 1-hour OHLCV data
def fetch_ohlcv(symbol, timeframe='1h', limit=200):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['timestamp'] = df['timestamp'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')  # Convert to UTC+5:30
        return df
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return pd.DataFrame()

# Function to calculate RSI using pandas_ta
def calculate_rsi(df, period=14):
    df['rsi'] = ta.rsi(df['close'], length=period)
    return df

# Function to check for buy signal based on Pine Script logic
def check_buy_signal(df, rsios=35, rsioslimit=40):
    buy_signal = None
    
    df['longConditionOne'] = (df['rsi'].shift(1) < rsios) & (df['rsi'] > rsios)
    df['longConditionTwo'] = (df['close'] > df['close'].shift(1)) & (df['rsi'] >= rsios)
    
    longConditionOne = False
    
    for i in range(1, len(df)):
        if df['longConditionOne'].iloc[i]:
            longConditionOne = True
        if df['rsi'].iloc[i] > rsioslimit:
            longConditionOne = False
        
        if longConditionOne and df['longConditionTwo'].iloc[i]:
            buy_signal = df['timestamp'].iloc[i]
            break

    return buy_signal

# Function to backtest the strategy
def backtest_strategy(symbol, df):
    initial_balance = 100  # Initial balance in USDT
    margin_per_trade = 2  # Margin per trade in USDT
    leverage = 10  # Leverage
    
    positions = []
    balance = initial_balance
    for i in range(1, len(df)):
        buy_signal = check_buy_signal(df.iloc[:i+1])
        if buy_signal:
            entry_price = df['close'].iloc[i]
            position_size = (margin_per_trade * leverage) / entry_price
            exit_price = entry_price * 1.02  # Exit at 2% profit
            profit = (exit_price - entry_price) * position_size
            balance += profit - margin_per_trade  # Deduct margin used for trade
            
            positions.append({
                'timestamp': df['timestamp'].iloc[i],
                'entry_price': entry_price,
                'exit_price': exit_price,
                'profit': profit,
                'balance': balance
            })

    return pd.DataFrame(positions)

# Main function to monitor and backtest markets
def monitor_and_backtest():
    markets = exchange.load_markets()
    future_pairs = [symbol for symbol in markets if symbol.endswith('USDT') and 'swap' in markets[symbol]['type']]
    print(future_pairs)
    
    # Monitor the markets
    while True:
        for symbol in future_pairs:
            df = fetch_ohlcv(symbol)
            if not df.empty:
                df = calculate_rsi(df)
                buy_signal = check_buy_signal(df)
                if buy_signal:
                    print(f"Buy signal for {symbol} at {buy_signal}")
                
                # Backtest the strategy
                backtest_results = backtest_strategy(symbol, df)
                print(backtest_results)
                
        time.sleep(3600)  # Wait for 1 hour before checking again

if __name__ == "__main__":
    monitor_and_backtest()
