import os
import logging
from flask import Flask
from telegram import Bot
from telegram.ext import Application, CommandHandler

# تنظیمات
BOT_TOKEN = os.environ.get('BOT_TOKEN')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ایجاد ربات
application = Application.builder().token(BOT_TOKEN).build()

# دستور ساده start
async def start(update, context):
    await update.message.reply_text(
        "👋 به ربات وام فرزند خوش آمدید!\n\n"
        "✅ سیستم فعال است\n"
        "برای ثبت‌نام آماده هستیم"
    )

# اضافه کردن هندلر
application.add_handler(CommandHandler("start", start))

# راه‌اندازی ربات در پس‌زمینه
def run_bot():
    try:
        logger.info("🤖 شروع ربات تلگرام...")
        application.run_polling()
    except Exception as e:
        logger.error(f"خطا در ربات: {e}")

# routes فلاسک
@app.route('/')
def home():
    return "✅ ربات فعال - /start را در تلگرام امتحان کنید", 200

@app.route('/test-bot')
def test_bot():
    try:
        bot = Bot(token=BOT_TOKEN)
        info = bot.get_me()
        return f"✅ ربات متصل است: {info.first_name}", 200
    except Exception as e:
        return f"❌ خطا: {e}", 500

if __name__ == "__main__":
    # تست اتصال ربات
    try:
        bot = Bot(token=BOT_TOKEN)
        info = bot.get_me()
        logger.info(f"✅ ربات: {info.first_name}")
    except Exception as e:
        logger.error(f"❌ خطا در اتصال ربات: {e}")
    
    # شروع ربات در ترد جداگانه
    import threading
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # شروع سرور
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"🌐 سرور روی پورت {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
