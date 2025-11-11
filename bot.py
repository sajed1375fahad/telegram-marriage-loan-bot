import os
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ ربات وام فرزند فعال است - Hello from Koyeb!", 200

@app.route('/health')
def health():
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
