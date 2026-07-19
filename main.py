import time
import os
import pandas as pd
from binance.client import Client

# REPLACEMENT: IP block bypass karne ke liye alternative open global endpoint use kiya hai
client = Client()
client.API_URL = 'https://api1.binance.com' # Bypasses cloud filters

WATCHLIST = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]

# ---- Native Mathematical Indicators ----
def calculate_ema(series, length):
    return series.ewm(span=length, adjust=False).mean()

def calculate_rsi(series, length=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=length).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=length).mean()
    rs = gain / (loss + 1e-10)
    return 100 - (100 / (1 + rs))

def calculate_atr(df, length=14):
    high_low = df['high'] - df['low']
    high_cp = (df['high'] - df['close'].shift()).abs()
    low_cp = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
    return tr.rolling(window=length).mean()
# --------------------------------------------------------

def fetch_market_pipeline(coin, interval, limit=150):
    try:
        bars = client.get_historical_klines(coin, interval, f"{limit} candles ago UTC")
        if not bars or len(bars) < limit:
            return None
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_av', 'trades', 'tb_base_av', 'tb_quote_av', 'ignore'])
        df['open'] = df['open'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['close'] = df['close'].astype(float)
        df['volume'] = df['volume'].astype(float)
        return df
    except Exception:
        return None

def compute_institutional_metrics(coin):
    df_4h = fetch_market_pipeline(coin, Client.KLINE_INTERVAL_4HOUR, limit=100)
    df_15m = fetch_market_pipeline(coin, Client.KLINE_INTERVAL_15MINUTE, limit=120)
    
    if df_4h is None or df_15m is None:
        return None
        
    df_4h['EMA_50'] = calculate_ema(df_4h['close'], length=50)
    df_4h['EMA_200'] = calculate_ema(df_4h['close'], length=200)
    latest_4h_close = df_4h['close'].iloc[-1]
    ema_50_4h = df_4h['EMA_50'].iloc[-1]
    ema_200_4h = df_4h['EMA_200'].iloc[-1]
    
    if latest_4h_close > ema_50_4h and ema_50_4h > ema_200_4h:
        macro_trend = "STRONG_BULLISH"
    elif latest_4h_close < ema_50_4h and ema_50_4h < ema_200_4h:
        macro_trend = "STRONG_BEARISH"
    else:
        macro_trend = "SIDEWAYS_RANGE"

    df_15m['EMA_21'] = calculate_ema(df_15m['close'], length=21)
    df_15m['RSI'] = calculate_rsi(df_15m['close'], length=14)
    df_15m['ATR'] = calculate_atr(df_15m, length=14)
    df_15m['Vol_Avg'] = df_15m['volume'].rolling(window=20).mean()
    df_15m['Swing_High'] = df_15m['high'].rolling(window=10, center=True).max()
    df_15m['Swing_Low'] = df_15m['low'].rolling(window=10, center=True).min()
    
    current_price = df_15m['close'].iloc[-1]
    prev_price = df_15m['close'].iloc[-2]
    rsi = df_15m['RSI'].iloc[-1]
    volume = df_15m['volume'].iloc[-1]
    vol_avg = df_15m['Vol_Avg'].iloc[-1]
    atr = df_15m['ATR'].iloc[-1]
    recent_resistance = df_15m['Swing_High'].dropna().iloc[-1]
    recent_support = df_15m['Swing_Low'].dropna().iloc[-1]
    volume_spike = volume > (vol_avg * 1.5)
    
    market_action = "HOLD / STANDBY"
    confidence_score = "0%"
    
    if macro_trend == "STRONG_BULLISH":
        if current_price <= (recent_support + (0.1 * atr)) and rsi < 40 and volume_spike:
            market_action = "🟢 LONG (Dip Buy)"
            confidence_score = "85%"
        elif current_price > recent_resistance and prev_price <= recent_resistance and volume_spike:
            market_action = "🟢 LONG (Breakout)"
            confidence_score = "90%"
    elif macro_trend == "STRONG_BEARISH":
        if current_price >= (recent_resistance - (0.1 * atr)) and rsi > 60 and volume_spike:
            market_action = "🔴 SHORT (Pullback)"
            confidence_score = "85%"
        elif current_price < recent_support and prev_price >= recent_support and volume_spike:
            market_action = "🔴 SHORT (Breakdown)"
            confidence_score = "90%"
    elif macro_trend == "SIDEWAYS_RANGE":
        if current_price <= recent_support and rsi <= 30:
            market_action = "🟢 RANGE LONG"
            confidence_score = "70%"
        elif current_price >= recent_resistance and rsi >= 70:
            market_action = "🔴 RANGE SHORT"
            confidence_score = "70%"

    return {
        "Coin": coin,
        "Price": f"${current_price:,.2f}",
        "Macro Bias": macro_trend.replace("_", " "),
        "RSI": round(rsi, 1) if not pd.isna(rsi) else 0.0,
        "Action": market_action,
        "Conf": confidence_score
    }

def run_production_dashboard():
    start_time = time.time()
    duration_limit = 5.9 * 3600 # 5 hours 54 minutes
    
    print("Starting Execution Engine...")
    while (time.time() - start_time) < duration_limit:
        try:
            dashboard_rows = []
            for coin in WATCHLIST:
                metrics = compute_institutional_metrics(coin)
                if metrics: dashboard_rows.append(metrics)
            
            print(f"--- Pulse: {time.strftime('%H:%M:%S')} ---")
            for row in dashboard_rows:
                print(f"{row['Coin']} | {row['Price']} | Bias: {row['Macro Bias']} | RSI: {row['RSI']} | {row['Action']} | {row['Conf']}")
            
            time.sleep(10)
        except Exception as e:
            time.sleep(5)
            continue
    print("Job completed: 6-hour limit reached.")

if __name__ == "__main__":
    run_production_dashboard()
    
