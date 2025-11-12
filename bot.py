import os
import logging
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes

# تنظیمات
BOT_TOKEN = os.environ.get('BOT_TOKEN')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ایجاد ربات
application = Application.builder().token(BOT_TOKEN).build()

# دستور ساده start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"📨 دستور start دریافت شد از: {update.effective_user.first_name}")
    await update.message.reply_text("✅ ربات فعال است! تست موفق.")

# هندلر ساده
application.add_handler(CommandHandler("start", start))

# راه‌اندازی webhook
def setup_bot():
    try:
        # حذف webhook قبلی
        application.bot.delete_webhook()
        
        # تنظیم webhook جدید
        webhook_url = "https://web-production-4644.up.railway.app/webhook"
        application.bot.set_webhook(webhook_url)
        logger.info(f"✅ Webhook تنظیم شد: {webhook_url}")
        
        # راه‌اندازی
        application.initialize()
        logger.info("✅ ربات راه‌اندازی شد")
        
        # تست ربات
        bot_info = application.bot.get_me()
        logger.info(f"✅ ربات: {bot_info.first_name} (@{bot_info.username})")
        
        return True
    except Exception as e:
        logger.error(f"❌ خطا: {e}")
        return False

# Webhook route
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        logger.info("📨 دریافت webhook")
        
        # پردازش update
        update = Update.de_json(request.get_json(), application.bot)
        application.process_update(update)
        
        logger.info("✅ پردازش موفق")
        return "OK", 200
        
    except Exception as e:
        logger.error(f"❌ خطا در پردازش: {e}")
        return "Error", 500

@app.route('/')
def home():
    return "✅ سرور فعال - از /start در ربات استفاده کنید", 200

@app.route('/setup')
def setup():
    success = setup_bot()
    return "✅ ربات تنظیم شد" if success else "❌ خطا در تنظیم", 200

@app.route('/debug')
def debug():
    try:
        bot = Bot(token=BOT_TOKEN)
        info = bot.get_me()
        return f"""
        <h1>دیباگ ربات</h1>
        <p>ربات: {info.first_name}</p>
        <p>یوزرنیم: @{info.username}</p>
        <p>آیدی: {info.id}</p>
        <p><a href="/setup">تنظیم مجدد</a></p>
        """
    except Exception as e:
        return f"❌ خطا: {e}"

# راه‌اندازی
if __name__ == "__main__":
    logger.info("🚀 شروع برنامه...")
    setup_bot()
    
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
