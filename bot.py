import os
import logging
from flask import Flask

# تنظیمات لاگ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ سیستم فعال - ربات در حال راه‌اندازی...", 200

@app.route('/health')
def health():
    return "OK", 200

@app.route('/test-bot')
def test_bot():
    """صفحه تست ربات"""
    try:
        BOT_TOKEN = os.environ.get('BOT_TOKEN')
        
        if not BOT_TOKEN:
            return "❌ توکن تنظیم نشده", 500
        
        # تست ساده ربات
        from telegram import Bot
        bot = Bot(token=BOT_TOKEN)
        info = bot.get_me()
        
        return f"✅ ربات متصل شد: {info.first_name} (@{info.username})", 200
        
    except Exception as e:
        return f"❌ خطا در ربات: {str(e)}", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"🚀 شروع برنامه روی پورت {port}")
    
    # تست ربات در همان ترد اصلی
    try:
        BOT_TOKEN = os.environ.get('BOT_TOKEN')
        if BOT_TOKEN:
            from telegram import Bot
            bot = Bot(token=BOT_TOKEN)
            info = bot.get_me()
            logger.info(f"✅ ربات متصل شد: {info.first_name}")
        else:
            logger.warning("⚠️ توکن تنظیم نشده")
    except Exception as e:
        logger.error(f"❌ خطا در ربات: {e}")
    
    app.run(host="0.0.0.0", port=port, debug=False)
