import os
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ ربات وام فرزند فعال روی Railway!", 200

@app.route('/health')
def health():
    return jsonify({"status": "active", "platform": "Railway"}), 200

@app.route('/api/test')
def test():
    return jsonify({"message": "API کار می‌کند!", "port": os.environ.get("PORT", "Not set")}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 در حال اجرا روی پورت: {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
