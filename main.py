import os
import time
import threading
import requests
import pkg_resources

from flask import Flask
from kucoin.client import Market, Trade

app = Flask(__name__)  # ✅ THIS LINE IS NEEDED HERE

# Load KuCoin credentials from environment
KUCOIN_API_KEY = os.getenv("KUCOIN_API_KEY")
KUCOIN_SECRET = os.getenv("KUCOIN_SECRET")
KUCOIN_PASSPHRASE = os.getenv("KUCOIN_API_PASSPHRASE")

# Initialize KuCoin client
client = Trade(key=KUCOIN_API_KEY, secret=KUCOIN_SECRET, passphrase=KUCOIN_PASSPHRASE)
market = Market()

# Background function for price checking
def monitor_price():
    while True:
        try:
            ticker = market.get_ticker("BTC-USDT")
            price = float(ticker["price"])
            print(f"Current BTC/USDT price: {price}")
        except Exception as e:
            print(f"[ERROR] {e}")
        time.sleep(10)

# Start background thread
threading.Thread(target=monitor_price, daemon=True).start()

@app.route("/")
def home():
    return "KuCoin bot running!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
