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

def init_db():
    try:
        conn = sqlite3.connect('users.db', check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                father_national_code TEXT,
                father_birth_date TEXT,
                father_province TEXT,
                father_city TEXT,
                father_phone TEXT,
                parents_separated BOOLEAN,
                mother_national_code TEXT,
                mother_birth_date TEXT,
                mother_phone TEXT,
                child_national_code TEXT,
                child_birth_date TEXT,
                child_province TEXT,
                child_city TEXT,
                child_number INTEGER,
                sms_code TEXT,
                tracking_code TEXT,
                created_at TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database created successfully")
    except Exception as e:
        logger.error(f"Database error: {e}")

init_db()

user_states = {}

REGISTRATION_STEPS = {
    'father_national_code': '🔢 <b>شماره ملی پدر</b> را وارد کنید:',
    'father_birth_date': '📅 <b>تاریخ تولد پدر</b> را به فرمت 1360/01/01 وارد کنید:',
    'father_province': '🏙️ <b>استان محل تولد پدر</b> را وارد کنید:',
    'father_city': '🏘️ <b>شهرستان محل تولد پدر</b> را وارد کنید:',
    'father_phone': '📱 <b>شماره تلفن همراه پدر</b> را وارد کنید:',
    'parents_status': '👨‍👩‍👧 <b>وضعیت والدین</b>:\n\nآیا والدین از هم جدا شده‌اند؟ (بله/خیر)',
    'mother_national_code': '🔢 <b>شماره ملی مادر</b> را وارد کنید:',
    'mother_birth_date': '📅 <b>تاریخ تولد مادر</b> را وارد کنید:',
    'mother_phone': '📱 <b>شماره تلفن همراه مادر</b> را وارد کنید:',
    'child_national_code': '🔢 <b>شماره ملی فرزند</b> را وارد کنید:',
    'child_birth_date': '📅 <b>تاریخ تولد فرزند</b> را به فرمت 1395/01/01 وارد کنید:',
    'child_province': '🏙️ <b>استان محل تولد فرزند</b> را وارد کنید:',
    'child_city': '🏘️ <b>شهرستان محل تولد فرزند</b> را وارد کنید:',
    'child_number': '👶 <b>فرزند چندم</b> هست؟\n(۱ برای فرزند اول، ۲ برای فرزند دوم و ...):'
}

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
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Send message error: {e}")
        return False

def create_yes_no_keyboard():
    return {
        'keyboard': [
            [{'text': '✅ بله'}, {'text': '❌ خیر'}]
        ],
        'resize_keyboard': True,
        'one_time_keyboard': True
    }

def create_child_number_keyboard():
    return {
        'keyboard': [
            [{'text': '۱'}, {'text': '۲'}, {'text': '۳'}],
            [{'text': '۴'}, {'text': '۵'}, {'text': '۶'}]
        ],
        'resize_keyboard': True,
        'one_time_keyboard': True
    }

def generate_sms_code():
    return str(random.randint(10000, 99999))

def start_registration(chat_id, username):
    user_states[chat_id] = {
        'step': 'father_national_code',
        'data': {},
        'username': username
    }
    
    send_telegram_message(chat_id, 
        "📝 <b>ثبت‌نام وام قرض الحسنه فرزند</b>\n\n"
        "لطفاً اطلاعات خواسته شده را به دقت وارد کنید.\n\n"
        + REGISTRATION_STEPS['father_national_code']
    )

def simulate_sms_verification(chat_id, phone_number):
    sms_code = generate_sms_code()
    
    if chat_id in user_states:
        user_states[chat_id]['data']['sms_code'] = sms_code
        user_states[chat_id]['step'] = 'sms_verification'
    
    send_telegram_message(chat_id,
        f"📲 <b>کد تأیید ۵ رقمی</b>\n\n"
        f"کد تأیید به شماره {phone_number} ارسال شد.\n\n"
        f"🔐 <b>کد تست:</b> <code>{sms_code}</code>\n\n"
        f"لطفاً کد را وارد کنید:"
    )

def validate_data(step, value):
    errors = {
        'father_national_code': lambda v: len(v) == 10 and v.isdigit() or "کد ملی باید 10 رقم باشد",
        'father_phone': lambda v: v.startswith('09') and len(v) == 11 and v.isdigit() or "شماره تلفن باید 11 رقم و با 09 شروع شود",
        'mother_national_code': lambda v: len(v) == 10 and v.isdigit() or "کد ملی باید 10 رقم باشد", 
        'mother_phone': lambda v: v.startswith('09') and len(v) == 11 and v.isdigit() or "شماره تلفن باید 11 رقم و با 09 شروع شود",
        'child_national_code': lambda v: len(v) == 10 and v.isdigit() or "کد ملی باید 10 رقم باشد",
        'child_number': lambda v: v.isdigit() and 1 <= int(v) <= 10 or "شماره فرزند باید بین 1 تا 10 باشد"
    }
    
    if step in errors:
        result = errors[step](value)
        if isinstance(result, str):
            return False, result
    return True, ""

def handle_registration_step(chat_id, text):
    if chat_id not in user_states:
        return
    
    user_data = user_states[chat_id]
    current_step = user_data['step']
    
    is_valid, error_msg = validate_data(current_step, text)
    if not is_valid:
        send_telegram_message(chat_id, f"❌ {error_msg}\n\nلطفاً مجدد وارد کنید:")
        return
    
    user_data['data'][current_step] = text
    
    next_step = None
    
    if current_step == 'father_national_code':
        next_step = 'father_birth_date'
    
    elif current_step == 'father_birth_date':
        next_step = 'father_province'
    
    elif current_step == 'father_province':
        next_step = 'father_city'
    
    elif current_step == 'father_city':
        next_step = 'father_phone'
    
    elif current_step == 'father_phone':
        next_step = 'parents_status'
        send_telegram_message(chat_id, REGISTRATION_STEPS['parents_status'], create_yes_no_keyboard())
        return
    
    elif current_step == 'parents_status':
        if text.lower() in ['بله', '✅ بله']:
            user_data['data']['parents_separated'] = True
            next_step = 'mother_national_code'
        else:
            user_data['data']['parents_separated'] = False
            next_step = 'child_national_code'
    
    elif current_step == 'mother_national_code':
        next_step = 'mother_birth_date'
    
    elif current_step == 'mother_birth_date':
        next_step = 'mother_phone'
    
    elif current_step == 'mother_phone':
        next_step = 'child_national_code'
    
    elif current_step == 'child_national_code':
        next_step = 'child_birth_date'
    
    elif current_step == 'child_birth_date':
        next_step = 'child_province'
    
    elif current_step == 'child_province':
        next_step = 'child_city'
    
    elif current_step == 'child_city':
        next_step = 'child_number'
        send_telegram_message(chat_id, REGISTRATION_STEPS['child_number'], create_child_number_keyboard())
        return
    
    elif current_step == 'child_number':
        phone_number = user_data['data'].get('father_phone')
        simulate_sms_verification(chat_id, phone_number)
        return
    
    elif current_step == 'sms_verification':
        correct_code = user_data['data'].get('sms_code')
        if text == correct_code:
            user_data['data']['sms_verified'] = True
            save_registration(chat_id, user_data['data'])
        else:
            send_telegram_message(chat_id, "❌ کد تأیید نادرست است. مجدد وارد کنید:")
        return
    
    if next_step:
        user_data['step'] = next_step
        send_telegram_message(chat_id, REGISTRATION_STEPS[next_step])

def save_registration(chat_id, data):
    try:
        conn = sqlite3.connect('users.db', check_same_thread=False)
        cursor = conn.cursor()
        
        tracking_code = f"TRK{int(datetime.now().timestamp())}"
        
        cursor.execute('''
            INSERT INTO users (
                chat_id, father_national_code, father_birth_date, father_province,
                father_city, father_phone, parents_separated, mother_national_code,
                mother_birth_date, mother_phone, child_national_code, child_birth_date,
                child_province, child_city, child_number, sms_code, tracking_code, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            chat_id,
            data.get('father_national_code'),
            data.get('father_birth_date'),
            data.get('father_province'),
            data.get('father_city'),
            data.get('father_phone'),
            data.get('parents_separated', False),
            data.get('mother_national_code'),
            data.get('mother_birth_date'),
            data.get('mother_phone'),
            data.get('child_national_code'),
            data.get('child_birth_date'),
            data.get('child_province'),
            data.get('child_city'),
            data.get('child_number'),
            data.get('sms_code'),
            tracking_code,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        summary = f"""
📋 <b>خلاصه ثبت‌نام:</b>

👤 <b>پدر:</b>
• کد ملی: {data.get('father_national_code')}
• تاریخ تولد: {data.get('father_birth_date')}
• استان: {data.get('father_province')}
• شهرستان: {data.get('father_city')}
• تلفن: {data.get('father_phone')}

{'👩 <b>مادر:</b>' if data.get('parents_separated') else ''}
{'• کد ملی: ' + data.get('mother_national_code') if data.get('parents_separated') else ''}
{'• تاریخ تولد: ' + data.get('mother_birth_date') if data.get('parents_separated') else ''}
{'• تلفن: ' + data.get('mother_phone') if data.get('parents_separated') else ''}

👶 <b>فرزند:</b>
• کد ملی: {data.get('child_national_code')}
• تاریخ تولد: {data.get('child_birth_date')}
• استان: {data.get('child_province')}
• شهرستان: {data.get('child_city')}
• فرزند: {data.get('child_number')}م
        """
        
        success_message = (
            "✅ <b>ثبت‌نام با موفقیت انجام شد!</b>\n\n"
            f"{summary}\n\n"
            f"📋 <b>کد رهگیری:</b> <code>{tracking_code}</code>\n\n"
            "🤖 ربات به صورت خودکار سامانه را بررسی می‌کند.\n\n"
            "📊 برای مشاهده وضعیت از /status استفاده کنید."
        )
        
        send_telegram_message(chat_id, success_message)
        
        if chat_id in user_states:
            del user_states[chat_id]
            
    except Exception as e:
        logger.error(f"Save error: {e}")
        send_telegram_message(chat_id, "❌ خطا در ثبت اطلاعات. لطفاً مجدد تلاش کنید.")

def handle_command(chat_id, command, username):
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
        send_telegram_message(chat_id, message)
    
    elif command == '/register':
        start_registration(chat_id, username)
    
    elif command == '/status':
        conn = sqlite3.connect('users.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users WHERE chat_id = ?', (chat_id,))
        count = cursor.fetchone()[0]
        conn.close()
        
        message = (
            "📊 <b>وضعیت سیستم</b>\n\n"
            f"• ثبت‌نام‌های شما: {count}\n"
            f"• وضعیت ربات: فعال ✅\n"
            f"• کاربر: @{username if username else 'ناشناس'}\n\n"
            "برای ثبت‌نام جدید از /register استفاده کنید."
        )
        send_telegram_message(chat_id, message)
    
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
        send_telegram_message(chat_id, message)
    
    else:
        if chat_id in user_states:
            handle_registration_step(chat_id, command)
        else:
            send_telegram_message(chat_id, "❌ دستور نامعتبر. از /start استفاده کنید.")

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        
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
                    send_telegram_message(chat_id, "از /start برای شروع استفاده کنید.")
        
        return "OK", 200
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
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
        
        if response.status_code == 200:
            return "✅ ربات تنظیم شد", 200
        else:
            return "❌ خطا در تنظیم", 500
            
    except Exception as e:
        return f"❌ خطا: {e}", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
