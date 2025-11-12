import os
import logging
from flask import Flask, request
import json
import requests

# تنظیمات
BOT_TOKEN = os.environ.get('BOT_TOKEN')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# تابع برای ارسال پیام به تلگرام
def send_telegram_message(chat_id, text):
    """ارسال پیام به تلگرام بدون استفاده از کتابخانه python-telegram-bot"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        response = requests.post(url, json=payload)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"خطا در ارسال پیام: {e}")
        return False

# پردازش دستورها
def handle_command(chat_id, command, username):
    """پردازش دستورهای ربات"""
    logger.info(f"دستور {command} از {username}")
    
    if command == '/start':
        message = (
            "👋 <b>به ربات وام فرزند خوش آمدید!</b>\n\n"
            "✅ <b>سیستم فعال و آماده است</b>\n\n"
            "📋 <b>دستورهای موجود:</b>\n"
            "/start - راهنمایی\n"
            "/register - ثبت‌نام وام\n"
            "/status - وضعیت سیستم\n"
            "/help - راهنمایی\n\n"
            "برای شروع از <b>/register</b> استفاده کنید."
        )
    
    elif command == '/register':
        message = (
            "📝 <b>ثبت‌نام وام فرزند</b>\n\n"
            "لطفاً نام و نام خانوادگی پدر را وارد کنید:"
        )
    
    elif command == '/status':
        message = (
            "📊 <b>وضعیت سیستم</b>\n\n"
            "• ربات: فعال ✅\n"
            "• سرور: Railway ✅\n"
            "• وضعیت: آماده ثبت‌نام\n"
            "• کاربر: @" + (username if username else "ناشناس")
        )
    
    elif command == '/help':
        message = (
            "📖 <b>راهنمای ربات</b>\n\n"
            "این ربات برای ثبت‌نام خودکار وام فرزند طراحی شده است.\n\n"
            "<b>دستورها:</b>\n"
            "/start - شروع کار\n"
            "/register - ثبت‌نام جدید\n" 
            "/status - وضعیت سیستم\n"
            "/help - نمایش این راهنما"
        )
    
    else:
        message = "❌ دستور نامعتبر. از /start استفاده کنید."
    
    # ارسال پیام
    success = send_telegram_message(chat_id, message)
    return success

# Webhook اصلی
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        logger.info(f"دریافت داده: {data}")
        
        if 'message' in data:
            message = data['message']
            chat_id = message['chat']['id']
            text = message.get('text', '')
            username = message['from'].get('username', '')
            
            # پردازش دستور
            if text.startswith('/'):
                handle_command(chat_id, text, username)
        
        return "OK", 200
        
    except Exception as e:
        logger.error(f"خطا در webhook: {e}")
        return "Error", 500

# تنظیم webhook در تلگرام
@app.route('/setup')
def setup():
    try:
        # حذف webhook قبلی
        delete_url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
        requests.get(delete_url)
        
        # تنظیم webhook جدید
        webhook_url = f"https://web-production-4644.up.railway.app/webhook"
        set_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={webhook_url}"
        response = requests.get(set_url)
        
        if response.status_code == 200:
            logger.info("✅ Webhook تنظیم شد")
            return "✅ ربات تنظیم شد و آماده است", 200
        else:
            logger.error(f"❌ خطا در تنظیم webhook: {response.text}")
            return "❌ خطا در تنظیم ربات", 500
            
    except Exception as e:
        logger.error(f"❌ خطا: {e}")
        return f"❌ خطا: {e}", 500

# صفحه اصلی
@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>ربات وام فرزند</title>
        <style>
            body { font-family: Tahoma; text-align: center; padding: 50px; }
            .success { color: green; font-weight: bold; }
        </style>
    </head>
    <body>
        <h1>🤖 ربات وام فرزند</h1>
        <p class="success">✅ سرور فعال است</p>
        <p><a href="/setup">تنظیم ربات</a></p>
        <p><a href="/test">تست ربات</a></p>
        <p>از /start در تلگرام استفاده کنید</p>
    </body>
    </html>
    """, 200

# تست ربات
@app.route('/test')
def test():
    try:
        # تست اتصال به تلگرام
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
        response = requests.get(url)
        
        if response.status_code == 200:
            bot_info = response.json()['result']
            return f"""
            <h1>✅ تست موفق</h1>
            <p>ربات: {bot_info['first_name']}</p>
            <p>یوزرنیم: @{bot_info['username']}</p>
            <p>آیدی: {bot_info['id']}</p>
            <p><a href="/setup">تنظیم ربات</a></p>
            """, 200
        else:
            return f"❌ خطا در اتصال: {response.text}", 500
            
    except Exception as e:
        return f"❌ خطا: {e}", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"🚀 شروع برنامه روی پورت {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
