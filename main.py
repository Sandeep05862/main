import os
import time
import threading
import requests
from flask import Flask
from kucoin.client import Market

app = Flask(__name__)

KUCOIN_API_KEY = os.getenv("KUCOIN_API_KEY")
KUCOIN_SECRET = os.getenv("KUCOIN_SECRET")
KUCOIN_PASSPHRASE = os.getenv("KUCOIN_API_PASSPHRASE")

market = Market()

# --- Helper Functions ---

def fetch_ohlc(symbol="BTC-USDT", interval="1min", limit=50):
    data = market.get_kline(symbol, interval, limit=limit)
    # Data comes in reverse: [time, open, close, high, low, volume, turnover]
    candles = [{
        "open": float(d[1]),
        "close": float(d[2]),
        "high": float(d[3]),
        "low": float(d[4]),
        "volume": float(d[5])
    } for d in reversed(data)]
    return candles

def heikin_ashi(candles):
    ha = []
    for i, c in enumerate(candles):
        ha_close = (c['open'] + c['high'] + c['low'] + c['close']) / 4
        if i == 0:
            ha_open = (c['open'] + c['close']) / 2
        else:
            ha_open = (ha[-1]['open'] + ha[-1]['close']) / 2
        ha_high = max(c['high'], ha_open, ha_close)
        ha_low = min(c['low'], ha_open, ha_close)
        ha.append({
            "open": ha_open,
            "close": ha_close,
            "high": ha_high,
            "low": ha_low,
            "volume": c['volume']
        })
    return ha

def calculate_rsi(candles, period=14):
    gains, losses = [], []
    for i in range(1, period + 1):
        change = candles[i]['close'] - candles[i - 1]['close']
        if change > 0:
            gains.append(change)
        else:
            losses.append(abs(change))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# --- Monitor Function ---

def monitor():
    while True:
        try:
            candles = fetch_ohlc()
            ha_candles = heikin_ashi(candles)
            rsi = calculate_rsi(ha_candles)
            volume_now = ha_candles[-1]['volume']
            volume_prev = ha_candles[-2]['volume']

            print(f"RSI: {rsi:.2f}, Volume Now: {volume_now:.2f}, Prev: {volume_prev:.2f}")

            if rsi < 30 and volume_now > volume_prev:
                print("🔔 Buy Signal (RSI oversold + Volume spike)")
            elif rsi > 70 and volume_now > volume_prev:
                print("🔔 Sell Signal (RSI overbought + Volume spike)")

        except Exception as e:
            print(f"[ERROR] {e}")
        time.sleep(60)

# --- Start Thread ---
threading.Thread(target=monitor, daemon=True).start()

@app.route("/")
def home():
    return "🚀 KuCoin Heikin-Ashi RSI Bot is Running!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
