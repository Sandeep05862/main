from flask import Flask
import os
import threading
import time
from kucoin.client import Client
import requests

# Load KuCoin credentials from environment variables
KUCOIN_API_KEY = os.getenv("KUCOIN_API_KEY")
KUCOIN_SECRET = os.getenv("KUCOIN_SECRET")
KUCOIN_PASSPHRASE = os.getenv("KUCOIN_PASSPHRASE")

# Load Telegram credentials from environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Initialize KuCoin client
client = Client(KUCOIN_API_KEY, KUCOIN_SECRET, KUCOIN_PASSPHRASE)

# Send message to Telegram
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            print("Telegram Error:", response.status_code, response.text)
    except Exception as e:
        print("Telegram Exception:", e)

# Bot logic
def run_bot():
    while True:
        try:
            ticker = client.get_ticker('BTC-USDT')
            price = ticker['price']
            send_telegram_message(f"🟢 BTC/USDT price: {price}")
            print(f"Price sent: {price}")
        except Exception as e:
            print("KuCoin Error:", e)
            send_telegram_message(f"❌ Error fetching price: {e}")
        time.sleep(60)

# Flask app setup
app = Flask(__name__)

@app.route('/')
def home():
    return 'SanKuCoin_bot is running in background!'

if __name__ == '__main__':
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()

    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
