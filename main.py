import os
import time
import requests
import pandas as pd
import numpy as np
from kucoin.client import Market
from flask import Flask
import threading
from datetime import datetime

# KuCoin API credentials
api_key = os.getenv("KUCOIN_API_KEY")
api_secret = os.getenv("KUCOIN_API_SECRET")
api_passphrase = os.getenv("KUCOIN_API_PASSPHRASE")

# Telegram bot credentials
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Create KuCoin Market client
client = Market()

# Flask App for Render health check
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print("Telegram Error:", e)

def get_heikin_ashi(df):
    ha_df = df.copy()
    ha_df['close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    ha_df['open'] = (df['open'].shift(1) + df['close'].shift(1)) / 2
    ha_df['high'] = df[['high', 'open', 'close']].max(axis=1)
    ha_df['low'] = df[['low', 'open', 'close']].min(axis=1)
    return ha_df.dropna()

def calculate_rsi(df, period=14):
    delta = df['close'].diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = pd.Series(gain).rolling(window=period).mean()
    avg_loss = pd.Series(loss).rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return pd.Series(rsi, index=df.index)

def fetch_klines(symbol, interval="5min", limit=100):
    try:
        data = client.get_kline(symbol=symbol, kline_type=interval)
        df = pd.DataFrame(data, columns=[
            "time", "open", "close", "high", "low", "volume", "turnover"])
        df["time"] = pd.to_datetime(pd.to_numeric(df["time"]), unit="s")
        df[["open", "close", "high", "low", "volume"]] = df[[
            "open", "close", "high", "low", "volume"]].astype(float)
        return df
    except Exception as e:
        print(f"Fetch Error for {symbol}: {e}")
        return None

def calculate_signals(symbol):
    df = fetch_klines(symbol)
    if df is None or len(df) < 20:
        return

    df = get_heikin_ashi(df)
    df["rsi"] = calculate_rsi(df)

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    signal = None
    if prev["rsi"] < 30 and latest["rsi"] > 30 and latest["close"] > prev["close"]:
        signal = "BUY"
    elif prev["rsi"] > 70 and latest["rsi"] < 70 and latest["close"] < prev["close"]:
        signal = "SELL"

    if signal:
        price = latest["close"]
        qty = round(25 / price, 3)
        timestamp = datetime.utcnow()

        if signal == "BUY":
            sl = round(df["low"].rolling(5).min().iloc[-1], 4)
            tp = round(price * 1.03, 4)
            msg = f"""📊 {symbol}
🟢 Signal: BUY
💰 Price: {price}
🎯 Qty: {qty}
❌ SL: {sl}
✅ TP: {tp}
🕒 Time: {timestamp}"""
        else:
            sl = round(df["high"].rolling(5).max().iloc[-1], 4)
            tp = round(price * 0.97, 4)
            msg = f"""📊 {symbol}
🔴 Signal: SELL
💰 Price: {price}
🎯 Qty: {qty}
❌ SL: {sl}
✅ TP: {tp}
🕒 Time: {timestamp}"""

        send_telegram_message(msg)

def get_top_volume_symbols():
    try:
        tickers = client.get_ticker()
        sorted_tickers = sorted(
            tickers["ticker"], key=lambda x: float(x["volValue"]), reverse=True)
        top_symbols = [t["symbol"] for t in sorted_tickers if t["symbol"].endswith("USDT")]
        return top_symbols[:10]
    except Exception as e:
        print("Volume Error:", e)
        return []

def run_bot():
    while True:
        symbols = get_top_volume_symbols()
        for sym in symbols:
            calculate_signals(sym)
            time.sleep(2)
        time.sleep(60 * 5)

# Start Flask and Bot Thread
if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=10000)
