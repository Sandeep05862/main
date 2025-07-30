from flask import Flask
import os
import threading
import time

# अपना बॉट का कोड यहां लिखो
def run_bot():
    while True:
        print("Sanbinance_bot is running")
        # यहां ट्रेडिंग लॉजिक लगाओ
        time.sleep(10)

# Flask App
app = Flask(__name__)

@app.route('/')
def home():
    return 'Sanbinance_bot is running in background!'

if __name__ == '__main__':
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()

    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
