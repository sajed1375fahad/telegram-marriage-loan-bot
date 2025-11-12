import os
import logging
import sqlite3
import random
from datetime import datetime
from flask import Flask, request
import requests

BOT_TOKEN = os.environ.get('BOT_TOKEN')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# دیتابیس
def init_db():
    try:
        conn = sqlite3.connect('users.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                father_name TEXT,
                created_at TEXT
            )
        ''')
        conn.commit()
        conn.close()
        logger.info("✅ Database ready")
    except Exception as e:
        logger.error(f"❌ Database error: {e}")

init_db()

user_states = {}

def send_telegram_message(chat_id, text, reply_markup=None):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        if reply_markup:
            payload['reply_markup'] = reply_markup
            
        response = requests.post(url, json=payload)
        logger.info(f"📤 Sent to {chat_id}: {text[:50]}... Status: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        logger.error(f"❌ Send error to {chat_id}: {e}")
        return False

def create_yes_no_keyboard():
    return {
        'keyboard': [[{'text': '✅ بله'}, {'text': '❌ خیر'}]],
        'resize_keyboard': True,
        'one_time_keyboard': True
    }

def start_registration(chat_id, username):
    logger.info(f"🚀 STARTING registration for {chat_id} (@{username})")
    user_states[chat_id] = {
        'step': 'father_national_code',
        'data': {},
        'username': username
    }
    send_telegram_message(chat_id, 
        "📝 <b>ثبت‌نام وام فرزند</b>\n\n"
        "🔢 <b>کد ملی پدر</b> را وارد کنید:"
    )

def handle_registration_step(chat_id, text):
    if chat_id not in user_states:
        logger.error(f"❌ User {chat_id} not found in registration states")
        send_telegram_message(chat_id, "❌ جلسه ثبت‌نام یافت نشد. /register رو دوباره بزنید.")
        return
    
    user_data = user_states[chat_id]
    current_step = user_data['step']
    
    logger.info(f"🔹 User {chat_id} at step '{current_step}' entered: '{text}'")
    
    # ذخیره داده
    user_data['data'][current_step] = text
    
    # پردازش مراحل
    if current_step == 'father_national_code':
        user_data['step'] = 'father_birth_date'
        send_telegram_message(chat_id, "📅 <b>تاریخ تولد پدر</b> (مثلاً 1360/01/01):")
    
    elif current_step == 'father_birth_date':
        user_data['step'] = 'father_province'
        send_telegram_message(chat_id, "🏙️ <b>استان محل تولد پدر</b>:")
    
    elif current_step == 'father_province':
        user_data['step'] = 'father_city'
        send_telegram_message(chat_id, "🏘️ <b>شهرستان محل تولد پدر</b>:")
    
    elif current_step == 'father_city':
        user_data['step'] = 'father_phone'
        send_telegram_message(chat_id, "📱 <b>شماره تلفن همراه پدر</b>:")
    
    elif current_step == 'father_phone':
        # اعتبارسنجی شماره تلفن
        if not text.startswith('09') or len(text) != 11 or not text.isdigit():
            logger.warning(f"❌ Invalid phone from {chat_id}: {text}")
            send_telegram_message(chat_id, "❌ شماره تلفن باید 11 رقم و با 09 شروع شود\n\nلطفاً مجدد وارد کنید:")
            return
        
        logger.info(f"✅ Valid phone from {chat_id}")
        user_data['step'] = 'parents_status'
        send_telegram_message(chat_id, 
            "👨‍👩‍👧 <b>وضعیت والدین</b>\n\nآیا والدین از هم جدا شده‌اند؟",
            create_yes_no_keyboard()
        )
    
    elif current_step == 'parents_status':
        logger.info(f"🔹 Parents status from {chat_id}: '{text}'")
        
        # پردازش پاسخ بدون اعتبارسنجی
        if text.lower() in ['بله', '✅ بله']:
            user_data['data']['parents_separated'] = True
            user_data['step'] = 'mother_national_code'
            send_telegram_message(chat_id, "🔢 <b>کد ملی مادر</b> را وارد کنید:")
        else:
            user_data['data']['parents_separated'] = False
            user_data['step'] = 'child_national_code'
            send_telegram_message(chat_id, "🔢 <b>کد ملی فرزند</b> را وارد کنید:")
    
    elif current_step == 'mother_national_code':
        user_data['step'] = 'mother_birth_date'
        send_telegram_message(chat_id, "📅 <b>تاریخ تولد مادر</b>:")
    
    elif current_step == 'mother_birth_date':
        user_data['step'] = 'mother_phone'
        send_telegram_message(chat_id, "📱 <b>شماره تلفن همراه مادر</b>:")
    
    elif current_step == 'mother_phone':
        user_data['step'] = 'child_national_code'
        send_telegram_message(chat_id, "🔢 <b>کد ملی فرزند</b> را وارد کنید:")
    
    elif current_step == 'child_national_code':
        user_data['step'] = 'child_birth_date'
        send_telegram_message(chat_id, "📅 <b>تاریخ تولد فرزند</b> (مثلاً 1395/01/01):")
    
    elif current_step == 'child_birth_date':
        user_data['step'] = 'child_province'
        send_telegram_message(chat_id, "🏙️ <b>استان محل تولد فرزند</b>:")
    
    elif current_step == 'child_province':
        user_data['step'] = 'child_city'
        send_telegram_message(chat_id, "🏘️ <b>شهرستان محل تولد فرزند</b>:")
    
    elif current_step == 'child_city':
        user_data['step'] = 'child_number'
        send_telegram_message(chat_id, "👶 <b>فرزند چندم</b> هست؟")
    
    elif current_step == 'child_number':
        # ثبت نهایی
        tracking_code = f"TRK{int(datetime.now().timestamp())}"
        logger.info(f"🎉 Registration completed for {chat_id} - Code: {tracking_code}")
        
        send_telegram_message(chat_id, 
            f"✅ <b>ثبت‌نام با موفقیت انجام شد!</b>\n\n"
            f"📋 <b>کد رهگیری:</b> <code>{tracking_code}</code>\n\n"
            "🤖 ربات به صورت خودکار سامانه را بررسی می‌کند."
        )
        
        # پاک کردن وضعیت
        del user_states[chat_id]

def handle_command(chat_id, command, username):
    logger.info(f"🔹 Command from {chat_id} (@{username}): {command}")
    
    if command == '/start':
        send_telegram_message(chat_id,
            "👋 <b>به ربات وام فرزند خوش آمدید!</b>\n\n"
            "📋 <b>دستورهای موجود:</b>\n"
            "/start - راهنمایی\n"
            "/register - ثبت‌نام\n"
            "/status - وضعیت\n\n"
            "برای شروع از <b>/register</b> استفاده کنید."
        )
    
    elif command == '/register':
        start_registration(chat_id, username)
    
    elif command == '/status':
        send_telegram_message(chat_id, 
            "📊 <b>وضعیت سیستم</b>\n\n"
            "• ربات: فعال ✅\n"
            "• سرور: Railway ✅\n"
            "• وضعیت: آماده ثبت‌نام"
        )
    
    else:
        if chat_id in user_states:
            logger.info(f"🔹 Processing as registration step: {command}")
            handle_registration_step(chat_id, command)
        else:
            send_telegram_message(chat_id, 
                "❌ دستور نامعتبر\n\n"
                "از /start برای شروع استفاده کنید."
            )

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        logger.info(f"📨 Webhook received from Telegram")
        
        if 'message' in data:
            message = data['message']
            chat_id = message['chat']['id']
            text = message.get('text', '').strip()
            username = message['from'].get('username', 'unknown')
            
            logger.info(f"🔹 Processing message: chat_id={chat_id}, text='{text}', user=@{username}")
            
            if text.startswith('/'):
                handle_command(chat_id, text, username)
            else:
                if chat_id in user_states:
                    handle_registration_step(chat_id, text)
                else:
                    send_telegram_message(chat_id, "از /start برای شروع استفاده کنید")
        
        return "OK", 200
        
    except Exception as e:
        logger.error(f"❌ Webhook processing error: {e}", exc_info=True)
        return "Error", 500

@app.route('/')
def home():
    return "✅ سرور فعال - ربات وام فرزند", 200

@app.route('/setup')
def setup():
    try:
        delete_url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
        requests.get(delete_url)
        
        webhook_url = f"https://web-production-4644.up.railway.app/webhook"
        set_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={webhook_url}"
        response = requests.get(set_url)
        
        logger.info(f"🔧 Webhook setup: {response.status_code} - {response.text}")
        return "✅ ربات تنظیم شد" if response.status_code == 200 else f"❌ خطا: {response.text}"
    except Exception as e:
        logger.error(f"❌ Setup error: {e}")
        return f"❌ خطا: {e}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"🚀 Starting bot on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
