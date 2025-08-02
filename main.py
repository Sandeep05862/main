import os
import requests
import pandas as pd
import time
from datetime import datetime
from kucoin.client import Market
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator

# 🔐 Environment variables
KUCOIN_API_KEY = os.getenv("KUCOIN_API_KEY")
KUCOIN_API_SECRET = os.getenv("KUCOIN_API_SECRET")
KUCOIN_API_PASSPHRASE = os.getenv("KUCOIN_API_PASSPHRASE")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 📈 KuCoin market client
client = Market()

# 📩 Telegram alerts
def send_telegram_alert(symbol, signal_type, price, qty, sl, tp):
    emoji = "🟢" if signal_type == "BUY" else "🔴"
    message = f"""
📊 {symbol}
{emoji} Signal: {signal_type}
💰 Price: {price}
🎯 Qty: {qty}
❌ SL: {sl}
✅ TP: {tp}
🕒 Time: {datetime.now()}
"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message})

# 🔁 Heikin Ashi calculation
def heikin_ashi(df):
    ha_df = df.copy()
    ha_df['HA_Close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    ha_open = [(df['open'][0] + df['close'][0]) / 2]
    for i in range(1, len(df)):
        ha_open.append((ha_open[i-1] + ha_df['HA_Close'][i-1]) / 2)
    ha_df['HA_Open'] = ha_open
    return ha_df

# 🧠 Strategy check
def check_signal(df):
    rsi = RSIIndicator(df['close'], window=14).rsi()
    df['rsi'] = rsi
    df['ema7'] = EMAIndicator(df['close'], window=7).ema_indicator()
    df['ema21'] = EMAIndicator(df['close'], window=21).ema_indicator()
    df['volume_avg'] = df['volume'].rolling(window=5).mean()

    if (
        df['ema7'].iloc[-1] > df['ema21'].iloc[-1] and
        df['rsi'].iloc[-1] < 70 and
        df['volume'].iloc[-1] > df['volume_avg'].iloc[-1]
    ):
        return "BUY"
    elif (
        df['ema7'].iloc[-1] < df['ema21'].iloc[-1] and
        df['rsi'].iloc[-1] > 30 and
        df['volume'].iloc[-1] > df['volume_avg'].iloc[-1]
    ):
        return "SELL"
    return None

# ⬇️ Fetch candle data
def fetch_ohlcv(symbol, interval, limit=100):
    raw = client.get_kline(symbol, interval, limit=limit)
    df = pd.DataFrame(raw, columns=['time', 'open', 'close', 'high', 'low', 'volume', 'turnover'])
    df["time"] = pd.to_datetime(pd.to_numeric(df["time"]), unit="ms")
    df = df.astype({"open": "float", "high": "float", "low": "float", "close": "float", "volume": "float"})
    return df

# 🎯 Calculate SL & TP
def calculate_sl_tp(df, direction):
    if direction == "BUY":
        sl = df["low"].iloc[-5:-1].min()
        tp = df["close"].iloc[-1] + (df["close"].iloc[-1] - sl) * 1.5
    else:
        sl = df["high"].iloc[-5:-1].max()
        tp = df["close"].iloc[-1] - (sl - df["close"].iloc[-1]) * 1.5
    return round(sl, 4), round(tp, 4)

# 💰 Quantity calculation (20x leverage, $10)
def calculate_qty(price):
    position_usd = 10 * 20  # leverage
    qty = position_usd / price
    return round(qty, 3)

# 📈 Top 10 coins by volume
def get_top_10_symbols():
    tickers = client.get_all_tickers()["ticker"]
    sorted_tickers = sorted(tickers, key=lambda x: float(x["volValue"]), reverse=True)
    top_symbols = [t["symbol"] for t in sorted_tickers if "USDT" in t["symbol"]][:10]
    return top_symbols

# 🚀 Run bot
def run_bot():
    while True:
        print("🔄 Scanning market...")
        symbols = get_top_10_symbols()

        for symbol in symbols:
            try:
                # Check 4H ➝ 15m ➝ 5m candles
                df_4h = fetch_ohlcv(symbol, "4hour")
                if check_signal(heikin_ashi(df_4h)) is None:
                    continue

                df_15m = fetch_ohlcv(symbol, "15min")
                if check_signal(heikin_ashi(df_15m)) is None:
                    continue

                df_5m = fetch_ohlcv(symbol, "5min")
                ha = heikin_ashi(df_5m)
                signal = check_signal(ha)

                if signal:
                    price = df_5m["close"].iloc[-1]
                    sl, tp = calculate_sl_tp(df_5m, signal)
                    qty = calculate_qty(price)
                    send_telegram_alert(symbol, signal, price, qty, sl, tp)

            except Exception as e:
                print(f"❌ Error for {symbol}: {e}")

        time.sleep(300)  # Wait 5 min

# ✅ Start bot
if __name__ == "__main__":
    run_bot()
