import os
import time
import requests
import pandas as pd
from kucoin.client import Market
from flask import Flask
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator

# 🔐 API Keys from Environment (Render में सेट करें)
api_key = os.getenv("KUCOIN_API_KEY")
api_secret = os.getenv("KUCOIN_API_SECRET")
api_passphrase = os.getenv("KUCOIN_API_PASSPHRASE")
bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")

client = Market(api_key, api_secret, api_passphrase)
app = Flask(__name__)

# 📩 Telegram Function
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": message})

# 📊 Heikin Ashi calculation
def heikin_ashi(df):
    df['HA_close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    df['HA_open'] = df['open'].copy()
    for i in range(1, len(df)):
        df.loc[i, 'HA_open'] = (df.loc[i-1, 'HA_open'] + df.loc[i-1, 'HA_close']) / 2
    return df

# 🔁 Signal check
def check_signal(df):
    rsi = RSIIndicator(close=df['close'], window=14).rsi()
    ma7 = SMAIndicator(close=df['close'], window=7).sma_indicator()
    ma21 = SMAIndicator(close=df['close'], window=21).sma_indicator()

    last_rsi = rsi.iloc[-1]
    vol = df['volume'].iloc[-1]

    buy = ma7.iloc[-2] < ma21.iloc[-2] and ma7.iloc[-1] > ma21.iloc[-1] and last_rsi < 30
    sell = ma7.iloc[-2] > ma21.iloc[-2] and ma7.iloc[-1] < ma21.iloc[-1] and last_rsi > 70

    return "BUY" if buy else "SELL" if sell else None

# 🎯 Signal detail + auto SL/TP
def trade_details(symbol, signal, price):
    qty = round(10 / price, 3)  # $10 position
    sl = round(price * 0.98, 4) if signal == "BUY" else round(price * 1.02, 4)
    tp = round(price * 1.03, 4) if signal == "BUY" else round(price * 0.97, 4)
    time_now = pd.Timestamp.now()

    message = (
        f"📊 {symbol}\n"
        f"{'🟢 Signal: BUY' if signal == 'BUY' else '🔴 Signal: SELL'}\n"
        f"💰 Price: {price}\n"
        f"🎯 Qty: {qty}\n"
        f"❌ SL: {sl}\n"
        f"✅ TP: {tp}\n"
        f"🕒 Time: {time_now}"
    )
    return message

# 🔍 Data fetch
def fetch_klines(symbol, interval):
    try:
        data = client.get_kline(symbol=symbol, kline_type=interval, limit=100)
        df = pd.DataFrame(data, columns=["time", "open", "close", "high", "low", "volume", "turnover"])
        df = df.astype(float)
        df["time"] = pd.to_datetime(pd.to_numeric(df["time"]), unit="s")
        return df
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None

# 🔝 Get top 10 coins
def get_top_10_symbols():
    tickers = client.get_all_tickers()["ticker"]
    sorted_tickers = sorted(tickers, key=lambda x: float(x["volValue"]), reverse=True)
    top_symbols = [t["symbol"] for t in sorted_tickers if "-USDT" in t["symbol"]][:10]
    return top_symbols

# 🔁 Main loop
def run_bot():
    symbols = get_top_10_symbols()
    for symbol in symbols:
        df_4h = fetch_klines(symbol, "4hour")
        df_15m = fetch_klines(symbol, "15min")
        df_5m = fetch_klines(symbol, "5min")

        if df_4h is None or df_15m is None or df_5m is None:
            continue

        for df in [df_4h, df_15m, df_5m]:
            df = heikin_ashi(df)

        signal_4h = check_signal(df_4h)
        signal_15m = check_signal(df_15m)
        signal_5m = check_signal(df_5m)

        if signal_4h and signal_4h == signal_15m == signal_5m:
            price = float(df_5m["close"].iloc[-1])
            message = trade_details(symbol, signal_5m, price)
            send_telegram_message(message)
        time.sleep(1)

# 🌐 Flask server for Render
@app.route("/")
def home():
    return "✅ Crypto bot is running!"

if __name__ == "__main__":
    while True:
        run_bot()
        time.sleep(300)  # हर 5 मिनट में दोबारा चलाएं
