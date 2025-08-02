import time, requests, math
import pandas as pd
from datetime import datetime
import pytz
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from kucoin_futures.client import Market, Trade

# KuCoin API
KUCOIN_API_KEY = 'YOUR_KUCOIN_API_KEY'
KUCOIN_API_SECRET = 'YOUR_KUCOIN_API_SECRET'
KUCOIN_API_PASSPHRASE = 'YOUR_KUCOIN_API_PASSPHRASE'

market = Market()
trade = Trade(key=KUCOIN_API_KEY, secret=KUCOIN_API_SECRET, passphrase=KUCOIN_API_PASSPHRASE)

# Telegram
TELEGRAM_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
TELEGRAM_CHAT_ID = 'YOUR_CHAT_ID'
TIMEZONE = pytz.timezone('Asia/Kolkata')

# Settings
INTERVAL = '5min'
QUANTITY_USDT = 10
LEVERAGE = 20

def send_telegram(symbol, signal, price, sl, qty):
    now = datetime.now(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')
    emoji = '🟢' if signal == 'BUY' else '🔴'
    msg = (
        f"{emoji} *{signal} Signal*\n\n"
        f"📌 Symbol: `{symbol}`\n"
        f"💰 Price: `{price}`\n"
        f"📦 Qty: `{qty}`\n"
        f"🛑 Stop Loss: `{sl}`\n"
        f"⏰ Time: `{now}`\n\n"
        f"#KuCoin #CryptoBot"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={'chat_id': TELEGRAM_CHAT_ID, 'text': msg, 'parse_mode': 'Markdown'})

def fetch_ohlcv(symbol):
    try:
        candles = market.get_kline(symbol, INTERVAL, 100)
        df = pd.DataFrame(candles, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
        df['close'] = df['close'].astype(float)
        df['low'] = df['low'].astype(float)
        df['high'] = df['high'].astype(float)
        return df
    except:
        return None

def apply_indicators(df):
    df['ema7'] = EMAIndicator(df['close'], window=7).ema_indicator()
    df['ema21'] = EMAIndicator(df['close'], window=21).ema_indicator()
    df['rsi'] = RSIIndicator(df['close']).rsi()
    return df

def calculate_swing(df):
    recent_lows = df['low'][-10:]
    recent_highs = df['high'][-10:]
    return min(recent_lows), max(recent_highs)

def set_leverage(symbol, leverage):
    try:
        trade.set_leverage(leverage=leverage, symbol=symbol)
    except Exception as e:
        print(f"Leverage Error: {e}")

def place_order(symbol, side, qty):
    try:
        order = trade.create_market_order(symbol=symbol, side=side.lower(), size=qty, leverage=LEVERAGE)
        return order
    except Exception as e:
        print(f"Order Error: {e}")
        return None

def get_price(symbol):
    try:
        return float(market.get_ticker(symbol)['price'])
    except:
        return None

def get_top_20_symbols():
    try:
        tickers = market.get_ticker()
        usdt_pairs = [t for t in tickers if t['symbol'].endswith('USDTM')]
        sorted_pairs = sorted(usdt_pairs, key=lambda x: float(x['volValue']), reverse=True)
        return [x['symbol'] for x in sorted_pairs[:20]]
    except:
        return ['BTCUSDTM']

def main():
    while True:
        symbols = get_top_20_symbols()
        for symbol in symbols:
            df = fetch_ohlcv(symbol)
            if df is None or df.empty:
                continue
            df = apply_indicators(df)
            last = df.iloc[-1]
            prev = df.iloc[-2]

            try:
                price = get_price(symbol)
                if not price:
                    continue
                qty = round((QUANTITY_USDT * LEVERAGE) / price, 3)
                sl_low, sl_high = calculate_swing(df)
                set_leverage(symbol, LEVERAGE)

                if prev['ema7'] < prev['ema21'] and last['ema7'] > last['ema21'] and last['rsi'] > 50:
                    place_order(symbol, 'BUY', qty)
                    send_telegram(symbol, 'BUY', price, sl_low, qty)

                elif prev['ema7'] > prev['ema21'] and last['ema7'] < last['ema21'] and last['rsi'] < 50:
                    place_order(symbol, 'SELL', qty)
                    send_telegram(symbol, 'SELL', price, sl_high, qty)

            except Exception as e:
                print(f"Error with {symbol}: {e}")

        time.sleep(300)

if __name__ == "__main__":
    main()
