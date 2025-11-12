import os
import logging
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# تنظیمات
BOT_TOKEN = os.environ.get('BOT_TOKEN')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ایجاد ربات
application = Application.builder().token(BOT_TOKEN).build()

# دستور start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 به ربات **اتوماسیون وام فرزند** خوش آمدید!\n\n"
        "📋 دستورهای موجود:\n"
        "/start - راهنمایی\n"
        "/register - ثبت‌نام وام\n"  
        "/status - وضعیت سیستم\n"
        "/help - راهنمایی\n\n"
        "برای شروع ثبت‌نام از /register استفاده کنید."
    )

# دستور register
async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📝 **ثبت‌نام وام فرزند**\n\n"
        "لطفاً نام و نام خانوادگی پدر را وارد کنید:"
    )

# دستور status
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📊 **وضعیت سیستم**:\n\n"
        "• ربات: فعال ✅\n"
        "• سرور: Railway ✅\n" 
        "• وضعیت: آماده ثبت‌نام\n"
        "• میزبان: Railway"
    )

# دستور help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 **راهنمای ربات**:\n\n"
        "این ربات برای ثبت‌نام خودکار وام فرزند طراحی شده است.\n\n"
        "دستورها:\n"
        "/start - شروع کار با ربات\n"
        "/register - ثبت‌نام جدید\n"
        "/status - وضعیت سیستم\n"
        "/help - نمایش این راهنما"
    )

# تنظیم هندلرها
def setup_handlers():
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("register", register))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("help", help_command))
    logger.info("✅ هندلرها ثبت شدند")

# راه‌اندازی webhook
def setup_webhook():
    try:
        # حذف webhook قبلی
        application.bot.delete_webhook()
        
        # تنظیم webhook جدید
        webhook_url = f"https://web-production-4644.up.railway.app/webhook"
        application.bot.set_webhook(webhook_url)
        logger.info(f"✅ Webhook تنظیم شد: {webhook_url}")
        
        # راه‌اندازی ربات
        application.initialize()
        logger.info("✅ ربات راه‌اندازی شد")
        
        return True
    except Exception as e:
        logger.error(f"❌ خطا در راه‌اندازی ربات: {e}")
        return False

# route برای webhook
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # لاگ درخواست
        logger.info("📨 دریافت webhook")
        
        update = Update.de_json(request.get_json(), application.bot)
        application.process_update(update)
        return "OK", 200
    except Exception as e:
        logger.error(f"❌ خطا در webhook: {e}")
        return "Error", 500

# routes دیگر
@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html dir="rtl">
    <head><meta charset="UTF-8"><title>ربات وام فرزند</title></head>
    <body style="font-family: Tahoma; text-align: center; padding: 50px;">
        <h1>🤖 ربات وام فرزند</h1>
        <p>ربات فعال است - از /start در تلگرام استفاده کنید</p>
        <p><a href="/setup">تنظیم مجدد ربات</a></p>
        <p><a href="/test-bot">تست اتصال</a></p>
    </body>
    </html>
    """, 200

@app.route('/test-bot')
def test_bot():
    try:
        bot = Bot(token=BOT_TOKEN)
        info = bot.get_me()
        return f"✅ ربات متصل است: {info.first_name} (@{info.username})", 200
    except Exception as e:
        return f"❌ خطا: {e}", 500

@app.route('/setup')
def setup():
    # ثبت هندلرها
    setup_handlers()
    
    # تنظیم webhook
    success = setup_webhook()
    
    if success:
        return "✅ ربات کامل تنظیم شد - دستورها فعال شدند", 200
    else:
        return "❌ خطا در تنظیم ربات", 500

# راه‌اندازی اولیه
setup_handlers()

if __name__ == "__main__":
    # تنظیم webhook
    setup_webhook()
    
    # شروع سرور
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"🌐 سرور روی پورت {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
