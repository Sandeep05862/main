import os
import time
import requests
import pandas as pd
import numpy as np
from flask import Flask
from kucoin.client import Market
from datetime import datetime
from ta.momentum import RSIIndicator

app = Flask(__name__)

# KuCoin client
client = Market()

# Telegram message sender
def send_telegram_message(message):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("Telegram Error:", e)

# Fetch KuCoin klines with retry on insufficient data
def fetch_klines(symbol="BTC-USDT", interval="1min", limit=100, retries=3, wait=10):
    for attempt in range(retries):
        try:
            klines = client.get_kline(symbol, interval, limit)
            df = pd.DataFrame(klines, columns=["time", "open", "close", "high", "low", "volume", "turnover"])
            df["time"] = pd.to_datetime(df["time"], unit="ms")
            df = df.astype(float)

            if len(df) < 30:
                print(f"Attempt {attempt+1}: Data not sufficient. Retrying in {wait} seconds...")
                time.sleep(wait)
                continue

            return df

        except Exception as e:
            print(f"Attempt {attempt+1}: Error fetching data - {e}")
            time.sleep(wait)

    print("❌ Data still insufficient after retries.")
    return None

# Heikin Ashi Calculation
def heikin_ashi(df):
    ha_df = df.copy()
    ha_df["HA_Close"] = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
    ha_open = [(df["open"][0] + df["close"][0]) / 2]
    for i in range(1, len(df)):
        ha_open.append((ha_open[i-1] + ha_df["HA_Close"][i-1]) / 2)
    ha_df["HA_Open"] = ha_open
    ha_df["HA_High"] = ha_df[["HA_Open", "HA_Close", "high"]].max(axis=1)
    ha_df["HA_Low"] = ha_df[["HA_Open", "HA_Close", "low"]].min(axis=1)
    return ha_df

# Strategy signal
def check_signal():
    df = fetch_klines()
    if df is None or len(df) < 30:
        return "📉 Data not sufficient"

    ha_df = heikin_ashi(df)
    rsi = RSIIndicator(close=df["close"], window=14).rsi()
    volume = df["volume"]

    rsi_latest = rsi.iloc[-1]
    rsi_prev = rsi.iloc[-2]
    vol_latest = volume.iloc[-1]
    vol_prev = volume.iloc[-2]
    ha_green = ha_df["HA_Close"].iloc[-1] > ha_df["HA_Open"].iloc[-1]

    if rsi_prev < 30 and rsi_latest > 30 and vol_latest > vol_prev and ha_green:
        signal = "✅ BUY Signal from RSI + Volume + Heikin Ashi"
        send_telegram_message(signal)
        return signal
    else:
        return "📊 No valid signal right now."

# Flask route
@app.route("/")
def home():
    try:
        result = check_signal()
        return result
    except Exception as e:
        return f"❌ Error occurred: {e}"

# Start Flask app
if __name__ == "__main__":
    send_telegram_message("✅ Telegram bot deployed and working on Render!")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
