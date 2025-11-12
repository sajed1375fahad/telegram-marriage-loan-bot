import os
import logging
import sqlite3
import random
from datetime import datetime
from flask import Flask, request
import requests

BOT_TOKEN = os.environ.get('BOT_TOKEN')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# دیتابیس ساده
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
        logger.error(f"❌ Database: {e}")

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
        logger.info(f"📤 Sent to {chat_id}: {text[:50]}...")
        return response.status_code == 200
    except Exception as e:
        logger.error(f"❌ Send error: {e}")
        return False

def create_yes_no_keyboard():
    return {
        'keyboard': [[{'text': '✅ بله'}, {'text': '❌ خیر'}]],
        'resize_keyboard': True,
        'one_time_keyboard': True
    }

def handle_registration_step(chat_id, text):
    if chat_id not in user_states:
        logger.error(f"❌ User {chat_id} not in states")
        return
    
    user_data = user_states[chat_id]
    current_step = user_data['step']
    
    logger.info(f"🔹 User {chat_id} at step '{current_step}' entered: '{text}'")
    
    # ذخیره داده
    user_data['data'][current_step] = text
    
    # تعیین مرحله بعد
    if current_step == 'father_national_code':
        user_data['step'] = 'father_birth_date'
        send_telegram_message(chat_id, "📅 تاریخ تولد پدر (1360/01/01):")
    
    elif current_step == 'father_birth_date':
        user_data['step'] = 'father_province'
        send_telegram_message(chat_id, "🏙️ استان محل تولد پدر:")
    
    elif current_step == 'father_province':
        user_data['step'] = 'father_city'
        send_telegram_message(chat_id, "🏘️ شهرستان محل تولد پدر:")
    
    elif current_step == 'father_city':
        user_data['step'] = 'father_phone'
        send_telegram_message(chat_id, "📱 شماره تلفن پدر:")
    
    elif current_step == 'father_phone':
        # فقط اینجا اعتبارسنجی کن
        if not text.startswith('09') or len(text) != 11 or not text.isdigit():
            send_telegram_message(chat_id, "❌ شماره تلفن باید 11 رقم و با 09 شروع شود")
            return
        
        user_data['step'] = 'parents_status'
        send_telegram_message(chat_id, 
            "👨‍👩‍👧 آیا والدین جدا شده‌اند؟",
            create_yes_no_keyboard()
        )
    
    elif current_step == 'parents_status':
        # هیچ اعتبارسنجی اینجا - فقط پردازش پاسخ
        logger.info(f"🔹 Parents status response: '{text}'")
        
        if text in ['بله', '✅ بله']:
            user_data['data']['parents_separated'] = True
            user_data['step'] = 'mother_national_code'
            send_telegram_message(chat_id, "🔢 کد ملی مادر:")
        else:
            user_data['data']['parents_separated'] = False
            user_data['step'] = 'child_national_code'
            send_telegram_message(chat_id, "🔢 کد ملی فرزند:")
    
    elif current_step == 'mother_national_code':
        user_data['step'] = 'mother_birth_date'
        send_telegram_message(chat_id, "📅 تاریخ تولد مادر:")
    
    elif current_step == 'mother_birth_date':
        user_data['step'] = 'mother_phone'
        send_telegram_message(chat_id, "📱 شماره تلفن مادر:")
    
    elif current_step == 'mother_phone':
        user_data['step'] = 'child_national_code'
        send_telegram_message(chat_id, "🔢 کد ملی فرزند:")
    
    elif current_step == 'child_national_code':
        user_data['step'] = 'child_birth_date'
        send_telegram_message(chat_id, "📅 تاریخ تولد فرزند:")
    
    elif current_step == 'child_birth_date':
        user_data['step'] = 'child_province'
        send_telegram_message(chat_id, "🏙️ استان محل تولد فرزند:")
    
    elif current_step == 'child_province':
        user_data['step'] = 'child_city'
        send_telegram_message(chat_id, "🏘️ شهرستان محل تولد فرزند:")
    
    elif current_step == 'child_city':
        user_data['step'] = 'child_number'
        send_telegram_message(chat_id, "👶 فرزند چندم؟")
    
    elif current_step == 'child_number':
        # ثبت نهایی
        tracking_code = f"TRK{int(datetime.now().timestamp())}"
        send_telegram_message(chat_id, f"✅ ثبت‌نام کامل!\nکد رهگیری: {tracking_code}")
        
        # پاک کردن وضعیت
        del user_states[chat_id]

def start_registration(chat_id, username):
    user_states[chat_id] = {
        'step': 'father_national_code',
        'data': {},
        'username': username
    }
    logger.info(f"🚀 Started registration for {chat_id}")
    send_telegram_message(chat_id, 
        "📝 ثبت‌نام وام فرزند\n\n🔢 کد ملی پدر را وارد کنید:"
    )

def handle_command(chat_id, command, username):
    logger.info(f"🔹 Command from {chat_id}: {command}")
    
    if command == '/start':
        send_telegram_message(chat_id,
            "👋 به ربات وام فرزند خوش آمدید!\n\n"
            "دستورها:\n"
            "/start - راهنما\n"
            "/register - ثبت‌نام\n"
            "/status - وضعیت"
        )
    
    elif command == '/register':
        start_registration(chat_id, username)
    
    elif command == '/status':
        send_telegram_message(chat_id, "✅ سیستم فعال است")
    
    else:
        if chat_id in user_states:
            handle_registration_step(chat_id, command)
        else:
            send_telegram_message(chat_id, "از /start استفاده کنید")

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        logger.info(f"📨 Webhook received: {data}")
        
        if 'message' in data:
            message = data['message']
            chat_id = message['chat']['id']
            text = message.get('text', '')
            username = message['from'].get('username', '')
            
            if text.startswith('/'):
                handle_command(chat_id, text, username)
            else:
                if chat_id in user_states:
                    handle_registration_step(chat_id, text)
                else:
                    send_telegram_message(chat_id, "از /start شروع کنید")
        
        return "OK", 200
        
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        return "Error", 500

@app.route('/')
def home():
    return "✅ سرور فعال", 200

@app.route('/setup')
def setup():
    try:
        delete_url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
        requests.get(delete_url)
        
        webhook_url = f"https://web-production-4644.up.railway.app/webhook"
        set_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={webhook_url}"
        response = requests.get(set_url)
        
        return "✅ ربات تنظیم شد" if response.status_code == 200 else "❌ خطا در تنظیم"
    except Exception as e:
        return f"❌ خطا: {e}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"🚀 Starting on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
