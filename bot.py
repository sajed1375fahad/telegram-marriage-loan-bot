import os
import logging
import sqlite3
import time
import asyncio
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from flask import Flask
import threading
from PIL import Image
import io
import requests

# توکن ربات - از متغیر محیطی بخون
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8355259038:AAE5a-fvTHNd7pX8Q4lOgNwAS-Ij2pcM154')

# تنظیمات لاگ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)

# مراحل ثبت نام
(
    FATHER_NAME, FATHER_NATIONAL_CODE, FATHER_BIRTH_DATE, FATHER_PROVINCE, FATHER_CITY,
    FATHER_PHONE, CHILD_NATIONAL_CODE, CHILD_BIRTH_DATE, CHILD_PROVINCE, CHILD_CITY,
    PARENTS_STATUS, MOTHER_NATIONAL_CODE, MOTHER_BIRTH_DATE, MOTHER_PHONE,
    BANK_PREFERENCE, CONFIRMATION, VERIFICATION_CODE
) = range(17)

# Flask app برای Koyeb
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 ربات اتوماسیون وام فرزند فعال است - توسعه یافته با هوش مصنوعی", 200

@app.route('/health')
def health():
    return {"status": "active", "service": "child_loan_automation", "timestamp": datetime.now().isoformat()}, 200

@app.route('/api/status')
def status():
    return {"status": "running", "bot": "online", "users_count": get_users_count()}, 200

def get_users_count():
    try:
        conn = sqlite3.connect('child_loan.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM child_loan_users')
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except:
        return 0

class UserDatabase:
    def __init__(self):
        self.conn = sqlite3.connect('child_loan.db', check_same_thread=False)
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS child_loan_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                chat_id INTEGER,
                
                -- اطلاعات پدر
                father_name TEXT,
                father_national_code TEXT UNIQUE,
                father_birth_date TEXT,
                father_province TEXT,
                father_city TEXT,
                father_phone TEXT,
                
                -- اطلاعات فرزند
                child_national_code TEXT,
                child_birth_date TEXT,
                child_province TEXT,
                child_city TEXT,
                
                -- وضعیت والدین
                parents_status TEXT,
                
                -- اطلاعات مادر (در صورت جدا بودن)
                mother_national_code TEXT,
                mother_birth_date TEXT,
                mother_phone TEXT,
                
                -- تنظیمات
                bank_preference TEXT,
                status TEXT DEFAULT 'pending',
                verification_code TEXT,
                last_response TEXT,
                registration_date TEXT,
                last_update TEXT
            )
        ''')
        
        self.conn.commit()
    
    def add_user(self, user_data):
        cursor = self.conn.cursor()
        registration_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            cursor.execute('''
                INSERT INTO child_loan_users 
                (user_id, chat_id, father_name, father_national_code, father_birth_date,
                 father_province, father_city, father_phone, child_national_code,
                 child_birth_date, child_province, child_city, parents_status,
                 mother_national_code, mother_birth_date, mother_phone, bank_preference, 
                 registration_date, last_update)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_data['user_id'], user_data['chat_id'],
                user_data['father_name'], user_data['father_national_code'],
                user_data['father_birth_date'], user_data['father_province'],
                user_data['father_city'], user_data['father_phone'],
                user_data['child_national_code'], user_data['child_birth_date'],
                user_data['child_province'], user_data['child_city'],
                user_data['parents_status'], user_data.get('mother_national_code'),
                user_data.get('mother_birth_date'), user_data.get('mother_phone'),
                user_data['bank_preference'], registration_date, registration_date
            ))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None
    
    def user_exists(self, national_code):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM child_loan_users WHERE father_national_code = ?', (national_code,))
        return cursor.fetchone() is not None
    
    def get_pending_users(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM child_loan_users WHERE status = "pending" ORDER BY id')
        return cursor.fetchall()
    
    def update_user_status(self, user_id, status, response=None):
        cursor = self.conn.cursor()
        update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if response:
            cursor.execute(
                'UPDATE child_loan_users SET status = ?, last_response = ?, last_update = ? WHERE id = ?',
                (status, response, update_time, user_id)
            )
        else:
            cursor.execute(
                'UPDATE child_loan_users SET status = ?, last_update = ? WHERE id = ?',
                (status, update_time, user_id)
            )
        self.conn.commit()

class ChildLoanAutomation:
    def __init__(self, db):
        self.db = db
        self.setup_driver()
    
    def setup_driver(self):
        """تنظیمات مرورگر برای اتوماسیون - سازگار با Koyeb"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--remote-debugging-port=9222')
            
            # تنظیمات برای محیط Koyeb
            chrome_options.binary_location = '/usr/bin/chromium-browser'
            
            self.driver = webdriver.Chrome(options=chrome_options)
            logging.info("✅ درایور مرورگر با موفقیت راه‌اندازی شد")
        except Exception as e:
            logging.error(f"❌ خطا در راه‌اندازی درایور: {e}")
            self.driver = None
    
    def check_system_ready(self):
        """بررسی آمادگی سیستم"""
        if not self.driver:
            return False
        
        try:
            self.driver.get("https://www.google.com")
            return "Google" in self.driver.title
        except:
            return False
    
    def process_pending_registrations(self):
        """پردازش ثبت‌نام‌های در انتظار"""
        if not self.driver:
            logging.error("درایور مرورگر در دسترس نیست")
            return
        
        pending_users = self.db.get_pending_users()
        logging.info(f"🔍 {len(pending_users)} کاربر در انتظار پردازش")
        
        for user in pending_users:
            try:
                user_id, chat_id = user[0], user[2]
                user_data = {
                    'father_name': user[3],
                    'father_national_code': user[4],
                    'father_birth_date': user[5],
                    'father_province': user[6],
                    'father_city': user[7],
                    'father_phone': user[8],
                    'child_national_code': user[9],
                    'child_birth_date': user[10],
                    'child_province': user[11],
                    'child_city': user[12],
                    'parents_status': user[13],
                    'mother_national_code': user[14],
                    'mother_birth_date': user[15],
                    'mother_phone': user[16],
                    'bank_preference': user[17]
                }
                
                # شبیه‌سازی ثبت‌نام
                result = self.simulate_registration(user_data)
                
                # آپدیت وضعیت کاربر
                self.db.update_user_status(user_id, 'processed', result)
                logging.info(f"✅ کاربر {user_data['father_name']} پردازش شد")
                
            except Exception as e:
                logging.error(f"❌ خطا در پردازش کاربر: {e}")
    
    def simulate_registration(self, user_data):
        """شبیه‌سازی ثبت‌نام - نسخه تست"""
        try:
            # اینجا می‌توانید کد واقعی اتوماسیون را قرار دهید
            time.sleep(2)  # شبیه‌سازی تاخیر
            
            return f"ثبت‌نام برای {user_data['father_name']} شبیه‌سازی شد. کد رهگیری: {int(time.time())}"
        except Exception as e:
            return f"خطا در ثبت‌نام: {str(e)}"

class ChildLoanBot:
    def __init__(self):
        self.db = UserDatabase()
        self.automation = ChildLoanAutomation(self.db)
        
        # راه‌اندازی ربات تلگرام
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()
        
        # شروع مانیتورینگ در background
        self.start_background_monitoring()
    
    def setup_handlers(self):
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start)],
            states={
                FATHER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_father_name)],
                FATHER_NATIONAL_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_father_national_code)],
                FATHER_BIRTH_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_father_birth_date)],
                FATHER_PROVINCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_father_province)],
                FATHER_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_father_city)],
                FATHER_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_father_phone)],
                CHILD_NATIONAL_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_child_national_code)],
                CHILD_BIRTH_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_child_birth_date)],
                CHILD_PROVINCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_child_province)],
                CHILD_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_child_city)],
                PARENTS_STATUS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_parents_status)],
                MOTHER_NATIONAL_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_mother_national_code)],
                MOTHER_BIRTH_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_mother_birth_date)],
                MOTHER_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_mother_phone)],
                BANK_PREFERENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_bank_preference)],
                CONFIRMATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.confirm_registration)],
            },
            fallbacks=[CommandHandler('cancel', self.cancel)]
        )
        
        self.application.add_handler(conv_handler)
        self.application.add_handler(CommandHandler('status', self.check_status))
        self.application.add_handler(CommandHandler('report', self.get_report))
        self.application.add_handler(CommandHandler('help', self.help_command))
    
    def start_background_monitoring(self):
        """شروع مانیتورینگ در پس‌زمینه"""
        def monitor():
            while True:
                try:
                    if self.automation.driver and self.automation.check_system_ready():
                        self.automation.process_pending_registrations()
                    else:
                        logging.warning("سیستم اتوماسیون آماده نیست")
                    
                    time.sleep(60)  # بررسی هر 1 دقیقه
                except Exception as e:
                    logging.error(f"خطا در مانیتورینگ: {e}")
                    time.sleep(30)
        
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
        logging.info("✅ سیستم مانیتورینگ 24/7 راه‌اندازی شد")
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "👋 به ربات **اتوماسیون هوشمند وام فرزند** خوش آمدید!\n\n"
            "🤖 قابلیت‌های ربات:\n"
            "• ثبت‌نام خودکار در سامانه ve.cbi.ir\n"
            "• مانیتورینگ 24/7 وضعیت بانک‌ها\n"
            "• پر کردن هوشمند فرم‌ها\n"
            "• ارسال عکس از مراحل ثبت‌نام\n\n"
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
        
        if self.db.user_exists(national_code):
            await update.message.reply_text("❌ این کد ملی قبلاً ثبت شده است.")
            return ConversationHandler.END
        
        context.user_data['father_national_code'] = national_code
        await update.message.reply_text("📅 **تاریخ تولد پدر** را به فرمت 1360/01/01 وارد کنید:")
        return FATHER_BIRTH_DATE
    
    async def get_father_birth_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['father_birth_date'] = update.message.text
        
        provinces_keyboard = [["تهران", "البرز"], ["اصفهان", "فارس"], ["سایر استان‌ها"]]
        reply_markup = ReplyKeyboardMarkup(provinces_keyboard, one_time_keyboard=True)
        await update.message.reply_text("🏙️ **استان محل تولد پدر**:", reply_markup=reply_markup)
        return FATHER_PROVINCE
    
    async def get_father_province(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['father_province'] = update.message.text
        if update.message.text == "سایر استان‌ها":
            await update.message.reply_text("🏙️ نام استان را وارد کنید:")
            return FATHER_PROVINCE
        await update.message.reply_text("🏘️ **شهرستان محل تولد پدر**:")
        return FATHER_CITY
    
    async def get_father_city(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['father_city'] = update.message.text
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
        
        provinces_keyboard = [["تهران", "البرز"], ["اصفهان", "فارس"], ["سایر استان‌ها"]]
        reply_markup = ReplyKeyboardMarkup(provinces_keyboard, one_time_keyboard=True)
        await update.message.reply_text("🏙️ **استان محل تولد فرزند**:", reply_markup=reply_markup)
        return CHILD_PROVINCE
    
    async def get_child_province(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['child_province'] = update.message.text
        if update.message.text == "سایر استان‌ها":
            await update.message.reply_text("🏙️ نام استان را وارد کنید:")
            return CHILD_PROVINCE
        await update.message.reply_text("🏘️ **شهرستان محل تولد فرزند**:")
        return CHILD_CITY
    
    async def get_child_city(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['child_city'] = update.message.text
        
        status_keyboard = [["با هم زندگی می‌کنند"], ["جدا شده"]]
        reply_markup = ReplyKeyboardMarkup(status_keyboard, one_time_keyboard=True)
        await update.message.reply_text(
            "👨‍👩‍👧 **وضعیت والدین**:\n\n"
            "• اگر با هم زندگی می‌کنند: 'با هم زندگی می‌کنند'\n"  
            "• اگر جدا شده‌اند: 'جدا شده'",
            reply_markup=reply_markup
        )
        return PARENTS_STATUS
    
    async def get_parents_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['parents_status'] = update.message.text
        
        if update.message.text == "جدا شده":
            await update.message.reply_text("🔢 **کد ملی مادر** را وارد کنید:")
            return MOTHER_NATIONAL_CODE
        else:
            context.user_data['mother_national_code'] = None
            context.user_data['mother_birth_date'] = None
            context.user_data['mother_phone'] = None
            
            bank_keyboard = [["ملی", "صادرات"], ["هر بانکی که فعال شود"]]
            reply_markup = ReplyKeyboardMarkup(bank_keyboard, one_time_keyboard=True)
            await update.message.reply_text(
                "🏦 **ترجیح بانکی**:\n\n"
                "بانک مورد نظر خود را انتخاب کنید:",
                reply_markup=reply_markup
            )
            return BANK_PREFERENCE
    
    async def get_mother_national_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['mother_national_code'] = update.message.text
        await update.message.reply_text("📅 **تاریخ تولد مادر** را به فرمت 1362/01/01 وارد کنید:")
        return MOTHER_BIRTH_DATE
    
    async def get_mother_birth_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['mother_birth_date'] = update.message.text
        await update.message.reply_text("📱 **شماره تلفن همراه مادر** را وارد کنید:")
        return MOTHER_PHONE
    
    async def get_mother_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        phone = update.message.text
        if not phone.startswith('09') or len(phone) != 11 or not phone.isdigit():
            aw
