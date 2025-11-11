import os
import logging
import sqlite3
import time
import asyncio
from datetime import datetime
from flask import Flask

# تنظیمات اولیه
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 ربات وام فرزند فعال است - توسعه یافته با هوش مصنوعی", 200

@app.route('/health')
def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}, 200

@app.route('/api/status')
def status():
    return {
        "status": "running", 
        "service": "child_loan_bot",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat()
    }, 200

# راه‌اندازی ساده و بدون مشکل
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    logging.info(f"🚀 شروع اپلیکیشن روی پورت {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
