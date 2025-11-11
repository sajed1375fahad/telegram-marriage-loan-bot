import os
import logging
import sqlite3
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from flask import Flask
import threading

# توکن ربات تلگرام
BOT_TOKEN = "8355259038:AAE5a-fvTHNd7pX8Q4lOgNwAS-Ij2pcM154"

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# مراحل ثبت نام
NAME, NATIONAL_CODE, PHONE, CONFIRMATION = range(4)

class UserDatabase:
    def __init__(self):
        self.conn = sqlite3.connect('users.db', check_same_thread=False)
        self.create_table()
    
    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT,
                national_code TEXT,
                phone TEXT,
                registration_date TEXT
            )
        ''')
        self.conn.commit()
    
    def add_user(self, user_id, name, national_code, phone):
        cursor = self.conn.cursor()
        registration_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('''
            INSERT INTO users (user_id, name, national_code, phone, registration_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, name, national_code, phone, registration_date))
        self.conn.commit()
    
    def user_exists(self, national_code):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users WHERE national_code = ?', (national_code,))
        return cursor.fetchone() is not None

# Flask app
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 ربات ثبت نام فعال است"

@app.route('/health')
def health():
    return "OK", 200

class LoanBot:
    def __init__(self):
        self.db = UserDatabase()
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start)],
            states={
                NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_name)],
                NATIONAL_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_national_code)],
                PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_phone)],
                CONFIRMATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.confirm_registration)],
            },
            fallbacks=[CommandHandler('cancel', self.cancel)]
        )
        
        self.application.add_handler(conv_handler)
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("👋 به ربات ثبت نام خوش آمدید!\nلطفاً نام و نام خانوادگی خود را وارد کنید:")
        return NAME
    
    async def get_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['name'] = update.message.text
        await update.message.reply_text("🔢 کد ملی خود را وارد کنید:")
        return NATIONAL_CODE
    
    async def get_national_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        national_code = update.message.text
        
        if not national_code.isdigit() or len(national_code) != 10:
            await update.message.reply_text("❌ کد ملی باید 10 رقم باشد. لطفاً مجدداً وارد کنید:")
            return NATIONAL_CODE
        
        if self.db.user_exists(national_code):
            await update.message.reply_text("❌ این کد ملی قبلاً ثبت شده است.")
            return ConversationHandler.END
        
        context.user_data['national_code'] = national_code
        await update.message.reply_text("📱 شماره تلفن خود را وارد کنید:")
        return PHONE
    
    async def get_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        phone = update.message.text
        
        if not phone.startswith('09') or len(phone) != 11 or not phone.isdigit():
            await update.message.reply_text("❌ شماره تلفن باید 11 رقم و با 09 شروع شود. لطفاً مجدداً وارد کنید:")
            return PHONE
        
        context.user_data['phone'] = phone
        
        user_data = context.user_data
        confirmation_text = (
            "📋 اطلاعات ثبت نام:\n\n"
            f"👤 نام: {user_data['name']}\n"
            f"🔢 کد ملی: {user_data['national_code']}\n"
            f"📱 تلفن: {user_data['phone']}\n\n"
            "آیا اطلاعات صحیح است؟ (بله/خیر)"
        )
        
        await update.message.reply_text(confirmation_text)
        return CONFIRMATION
    
    async def confirm_registration(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        response = update.message.text.lower()
        
        if response in ['بله', 'yes', 'y', '✅']:
            user_data = context.user_data
            self.db.add_user(
                update.effective_user.id,
                user_data['name'],
                user_data['national_code'],
                user_data['phone']
            )
            
            await update.message.reply_text("✅ ثبت نام با موفقیت انجام شد!\nبرای ثبت نام جدید /start را بزنید.")
        else:
            await update.message.reply_text("❌ ثبت نام لغو شد.\nبرای شروع مجدد /start را بزنید.")
        
        return ConversationHandler.END
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("❌ عملیات لغو شد.")
        return ConversationHandler.END
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🤖 برای شروع ثبت نام /start را وارد کنید.")

def run_bot():
    """اجرای ربات"""
    try:
        bot = LoanBot()
        print("🤖 ربات در حال راه‌اندازی...")
        asyncio.run(bot.application.run_polling(drop_pending_updates=True))
    except Exception as e:
        print(f"❌ خطا در اجرای ربات: {e}")

def run_flask():
    """اجرای Flask"""
    try:
        port = int(os.getenv('PORT', 8000))
        print(f"🌐 Flask روی پورت {port}")
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    except Exception as e:
        print(f"❌ خطا در Flask: {e}")

if __name__ == "__main__":
    print("🔧 شروع راه‌اندازی...")
    
    # فقط Flask رو اجرا کن - ربات رو حذف کردیم
    run_flask()
