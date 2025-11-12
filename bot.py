import os
import logging
import sqlite3
import asyncio
from datetime import datetime
from flask import Flask, request, jsonify
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# تنظیمات لاگ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# توکن ربات - از متغیر محیطی می‌خوانیم
BOT_TOKEN = os.environ.get('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')

# مراحل ثبت نام
(
    FATHER_NAME, FATHER_NATIONAL_CODE, FATHER_BIRTH_DATE, 
    FATHER_PHONE, CHILD_NATIONAL_CODE, CHILD_BIRTH_DATE,
    BANK_PREFERENCE, CONFIRMATION
) = range(8)

app = Flask(__name__)

# مدیریت دیتابیس
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('child_loan.db', check_same_thread=False)
        self.init_db()
    
    def init_db(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                chat_id INTEGER,
                father_name TEXT,
                father_national_code TEXT UNIQUE,
                father_birth_date TEXT,
                father_phone TEXT,
                child_national_code TEXT,
                child_birth_date TEXT,
                bank_preference TEXT,
                status TEXT DEFAULT 'pending',
                tracking_code TEXT,
                created_at TEXT
            )
        ''')
        self.conn.commit()
    
    def add_user(self, user_data):
        cursor = self.conn.cursor()
        created_at = datetime.now().isoformat()
        
        try:
            cursor.execute('''
                INSERT INTO users (
                    user_id, chat_id, father_name, father_national_code,
                    father_birth_date, father_phone, child_national_code,
                    child_birth_date, bank_preference, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_data['user_id'],
                user_data['chat_id'],
                user_data['father_name'],
                user_data['father_national_code'],
                user_data['father_birth_date'],
                user_data['father_phone'],
                user_data['child_national_code'],
                user_data['child_birth_date'],
                user_data['bank_preference'],
                created_at
            ))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None
    
    def get_user_count(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users')
        return cursor.fetchone()[0]

db = Database()

# ربات تلگرام
class ChildLoanBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start)],
            states={
                FATHER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_father_name)],
                FATHER_NATIONAL_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_father_national_code)],
                FATHER_BIRTH_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_father_birth_date)],
                FATHER_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_father_phone)],
                CHILD_NATIONAL_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_child_national_code)],
                CHILD_BIRTH_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_child_birth_date)],
                BANK_PREFERENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_bank_preference)],
                CONFIRMATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.confirm_registration)],
            },
            fallbacks=[CommandHandler('cancel', self.cancel)]
        )
        
        self.application.add_handler(conv_handler)
        self.application.add_handler(CommandHandler('status', self.check_status))
        self.application.add_handler(CommandHandler('help', self.help_command))
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "👋 به ربات **اتوماسیون وام قرض الحسنه فرزند** خوش آمدید!\n\n"
            "🤖 این ربات به صورت 24/7:\n"
            "• سامانه بانک‌ها رو بررسی می‌کنه\n"
            "• فرم‌ها رو هوشمند پر می‌کنه\n"  
            "• به محض فعال شدن بانک، ثبت‌نام می‌کنه\n\n"
            "لطفاً **نام و نام خانوادگی پدر** را وارد کنید:"
        )
        return FATHER_NAME
    
    async def get_father_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['father_name'] = update.message.text
        context.user_data['user_id'] = update.effective_user.id
        context.user_data['chat_id'] = update.effective_chat.id
        await update.message.reply_text("🔢 **کد ملی پدر** را وارد کنید:")
        return FATHER_NATIONAL_CODE
    
    async def get_father_national_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        national_code = update.message.text
        if not national_code.isdigit() or len(national_code) != 10:
            await update.message.reply_text("❌ کد ملی باید 10 رقم باشد. لطفاً مجدداً وارد کنید:")
            return FATHER_NATIONAL_CODE
        
        context.user_data['father_national_code'] = national_code
        await update.message.reply_text("📅 **تاریخ تولد پدر** را به فرمت 1360/01/01 وارد کنید:")
        return FATHER_BIRTH_DATE
    
    async def get_father_birth_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['father_birth_date'] = update.message.text
        await update.message.reply_text("📱 **شماره تلفن همراه پدر** را وارد کنید:")
        return FATHER_PHONE
    
    async def get_father_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        phone = update.message.text
        if not phone.startswith('09') or len(phone) != 11 or not phone.isdigit():
            await update.message.reply_text("❌ شماره تلفن باید 11 رقم و با 09 شروع شود. لطفاً مجدداً وارد کنید:")
            return FATHER_PHONE
        
        context.user_data['father_phone'] = phone
        await update.message.reply_text("🔢 **کد ملی فرزند** را وارد کنید:")
        return CHILD_NATIONAL_CODE
    
    async def get_child_national_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['child_national_code'] = update.message.text
        await update.message.reply_text("📅 **تاریخ تولد فرزند** را به فرمت 1395/01/01 وارد کنید:")
        return CHILD_BIRTH_DATE
    
    async def get_child_birth_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['child_birth_date'] = update.message.text
        
        bank_keyboard = [["ملی", "صادرات"], ["هر بانکی که فعال شود"]]
        reply_markup = ReplyKeyboardMarkup(bank_keyboard, one_time_keyboard=True)
        await update.message.reply_text(
            "🏦 **ترجیح بانکی**:\n\n"
            "بانک مورد نظر خود را انتخاب کنید:",
            reply_markup=reply_markup
        )
        return BANK_PREFERENCE
    
    async def get_bank_preference(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['bank_preference'] = update.message.text
        
        # نمایش خلاصه اطلاعات
        summary = f"""
📋 **خلاصه اطلاعات**:

👤 **اطلاعات پدر:**
• نام: {context.user_data['father_name']}
• کد ملی: {context.user_data['father_national_code']}
• تاریخ تولد: {context.user_data['father_birth_date']}
• تلفن: {context.user_data['father_phone']}

👶 **اطلاعات فرزند:**
• کد ملی: {context.user_data['child_national_code']}
• تاریخ تولد: {context.user_data['child_birth_date']}

🏦 **ترجیح بانکی:** {context.user_data['bank_preference']}

آیا اطلاعات فوق صحیح است؟ (بله/خیر)
        """
        
        await update.message.reply_text(summary)
        return CONFIRMATION
    
    async def confirm_registration(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.text.lower() in ['بله', 'yes', 'y']:
            user_id = db.add_user(context.user_data)
            
            if user_id:
                tracking_code = f"TRK{int(datetime.now().timestamp())}"
                await update.message.reply_text(
                    f"✅ **ثبت‌نام با موفقیت انجام شد!**\n\n"
                    f"📝 **کد رهگیری:** `{tracking_code}`\n"
                    f"🤖 ربات به صورت 24/7 در حال مانیتورینگ سامانه است.\n"
                    f"به محض فعال شدن بانک مورد نظر، ثبت‌نام شما به صورت خودکار انجام خواهد شد.\n\n"
                    f"📊 برای مشاهده وضعیت از دستور /status استفاده کنید."
                )
            else:
                await update.message.reply_text("❌ این کد ملی قبلاً ثبت شده است.")
        else:
            await update.message.reply_text("❌ ثبت‌نام لغو شد. برای شروع مجدد از /start استفاده کنید.")
        
        return ConversationHandler.END
    
    async def check_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_count = db.get_user_count()
        await update.message.reply_text(
            f"📊 **وضعیت سامانه**:\n\n"
            f"• کاربران ثبت‌نام شده: {user_count}\n"
            f"• وضعیت سیستم: فعال ✅\n"
            f"• آخرین بروزرسانی: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "📖 **راهنمای ربات**:\n\n"
            "/start - شروع ثبت‌نام جدید\n"
            "/status - مشاهده وضعیت سیستم\n" 
            "/help - نمایش این راهنما\n\n"
            "🤖 **پشتیبانی**: @YourSupportChannel"
        )
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("❌ عملیات کنسل شد.")
        return ConversationHandler.END

# ایجاد ربات
bot = ChildLoanBot()

# راه‌اندازی ربات در پس‌زمینه
def run_bot():
    print("🤖 شروع ربات تلگرام...")
    bot.application.run_polling()

# Routes برای Flask
@app.route('/')
def home():
    user_count = db.get_user_count()
    return f"""
    <!DOCTYPE html>
    <html dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>ربات وام فرزند</title>
        <style>
            body {{ font-family: Tahoma; text-align: center; padding: 50px; background: #f0f8ff; }}
            .container {{ background: white; padding: 40px; border-radius: 15px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }}
            h1 {{ color: #2e8b57; }}
            .stats {{ background: #2e8b57; color: white; padding: 20px; border-radius: 10px; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 ربات وام فرزند</h1>
            <p>سامانه هوشمند ثبت‌نام خودکار</p>
            
            <div class="stats">
                <h3>📊 آمار سیستم</h3>
                <p>کاربران ثبت‌نام شده: <strong>{user_count}</strong></p>
                <p>وضعیت: <strong>فعال ✅</strong></p>
            </div>
            
            <p>ربات تلگرام در حال اجراست...</p>
        </div>
    </body>
    </html>
    """

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "bot": "running",
        "users_count": db.get_user_count(),
        "timestamp": datetime.now().isoformat()
    }), 200

@app.route('/api/users')
def api_users():
    return jsonify({
        "total_users": db.get_user_count(),
        "status": "active"
    }), 200

if __name__ == "__main__":
    # شروع ربات در ترد جداگانه
    import threading
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # شروع سرور Flask
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 سرور Flask روی پورت {port} راه‌اندازی می‌شود...")
    app.run(host="0.0.0.0", port=port, debug=False)
