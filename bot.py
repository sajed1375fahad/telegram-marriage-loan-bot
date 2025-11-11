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
from flask import Flask
import threading
from PIL import Image
import io

# توکن ربات
BOT_TOKEN = "8355259038:AAE5a-fvTHNd7pX8Q4lOgNwAS-Ij2pcM154"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
    return "🤖 ربات اتوماسیون وام فرزند فعال است"

@app.route('/health')
def health():
    return "OK", 200

@app.route('/api/status')
def status():
    return {"status": "active", "service": "child_loan_automation", "timestamp": datetime.now().isoformat()}

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
                registration_date TEXT
            )
        ''')
        
        self.conn.commit()
    
    def add_user(self, user_data):
        cursor = self.conn.cursor()
        registration_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute('''
            INSERT INTO child_loan_users 
            (user_id, chat_id, father_name, father_national_code, father_birth_date,
             father_province, father_city, father_phone, child_national_code,
             child_birth_date, child_province, child_city, parents_status,
             mother_national_code, mother_birth_date, mother_phone, bank_preference, registration_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_data['user_id'], user_data['chat_id'],
            user_data['father_name'], user_data['father_national_code'],
            user_data['father_birth_date'], user_data['father_province'],
            user_data['father_city'], user_data['father_phone'],
            user_data['child_national_code'], user_data['child_birth_date'],
            user_data['child_province'], user_data['child_city'],
            user_data['parents_status'], user_data.get('mother_national_code'),
            user_data.get('mother_birth_date'), user_data.get('mother_phone'),
            user_data['bank_preference'], registration_date
        ))
        self.conn.commit()
        return cursor.lastrowid
    
    def user_exists(self, national_code):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM child_loan_users WHERE father_national_code = ?', (national_code,))
        return cursor.fetchone() is not None
    
    def get_pending_users(self, bank_name=None):
        cursor = self.conn.cursor()
        if bank_name and bank_name != "هر بانکی که فعال شود":
            cursor.execute(
                'SELECT * FROM child_loan_users WHERE status = "pending" AND bank_preference = ? ORDER BY id',
                (bank_name,)
            )
        else:
            cursor.execute('SELECT * FROM child_loan_users WHERE status = "pending" ORDER BY id')
        return cursor.fetchall()
    
    def update_user_status(self, user_id, status, verification_code=None, response=None):
        cursor = self.conn.cursor()
        if verification_code:
            cursor.execute(
                'UPDATE child_loan_users SET status = ?, verification_code = ?, last_response = ? WHERE id = ?',
                (status, verification_code, response, user_id)
            )
        elif response:
            cursor.execute(
                'UPDATE child_loan_users SET status = ?, last_response = ? WHERE id = ?',
                (status, response, user_id)
            )
        else:
            cursor.execute('UPDATE child_loan_users SET status = ? WHERE id = ?', (status, user_id))
        self.conn.commit()

class ChildLoanAutomation:
    def __init__(self, application):
        self.application = application
        self.db = UserDatabase()
        self.setup_driver()
    
    def setup_driver(self):
        """تنظیمات مرورگر برای اتوماسیون"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')
        
        self.driver = webdriver.Chrome(options=chrome_options)
    
    def take_screenshot(self):
        """گرفتن عکس از صفحه"""
        screenshot = self.driver.get_screenshot_as_png()
        return io.BytesIO(screenshot)
    
    def smart_form_filler(self, user_data):
        """پر کردن هوشمند فرم وام فرزند"""
        try:
            logging.info(f"شروع ثبت‌نام برای {user_data['father_name']}")
            
            # رفتن به صفحه سامانه
            self.driver.get("http://ve.cbi.ir")
            time.sleep(5)
            
            # اطلاعات پدر
            self.fill_field("شماره ملی پدر", user_data['father_national_code'])
            self.fill_field("تاریخ تولد پدر", user_data['father_birth_date'])
            self.select_dropdown("استان محل تولد پدر", user_data['father_province'])
            self.select_dropdown("شهرستان محل تولد پدر", user_data['father_city'])
            self.fill_field("شماره تلفن همراه پدر", user_data['father_phone'])
            
            # اطلاعات فرزند
            self.fill_field("شماره ملی فرزند", user_data['child_national_code'])
            self.fill_field("تاریخ تولد فرزند", user_data['child_birth_date'])
            self.select_dropdown("استان محل تولد فرزند", user_data['child_province'])
            self.select_dropdown("شهرستان محل تولد فرزند", user_data['child_city'])
            
            # وضعیت والدین
            if user_data['parents_status'] == "جدا شده":
                # تیک زدن گزینه جدا شدن والدین
                checkbox = self.driver.find_element(By.XPATH, "//input[@type='checkbox' and contains(@name, 'جدا')]")
                checkbox.click()
                time.sleep(1)
                
                # پر کردن اطلاعات مادر
                self.fill_field("شماره ملی مادر", user_data['mother_national_code'])
                self.fill_field("تاریخ تولد مادر", user_data['mother_birth_date'])
                self.fill_field("شماره تلفن همراه مادر", user_data['mother_phone'])
            
            # گرفتن عکس از فرم پر شده
            filled_screenshot = self.take_screenshot()
            
            # ارسال فرم
            submit_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'ثبت')]")
            if submit_buttons:
                submit_buttons[0].click()
                time.sleep(5)
                
                # گرفتن عکس از نتیجه
                result_screenshot = self.take_screenshot()
                
                # بررسی نتیجه
                page_source = self.driver.page_source
                if "موفق" in page_source or "ثبت شد" in page_source:
                    return "success", filled_screenshot, result_screenshot
                elif "کد رهگیری" in page_source or "پیامک" in page_source:
                    return "need_verification", filled_screenshot, result_screenshot
                else:
                    return "unknown", filled_screenshot, result_screenshot
            else:
                return "no_submit_button", filled_screenshot, None
                
        except Exception as e:
            logging.error(f"خطا در پر کردن فرم: {e}")
            return "error", None, None
    
    def fill_field(self, field_label, value):
        """پر کردن فیلد بر اساس لیبل"""
        try:
            # روش اول: پیدا کردن فیلد با لیبل
            field = self.driver.find_element(By.XPATH, f"//label[contains(text(), '{field_label}')]/following-sibling::input")
            field.clear()
            field.send_keys(value)
            time.sleep(1)
        except:
            try:
                # روش دوم: پیدا کردن با placeholder
                field = self.driver.find_element(By.XPATH, f"//input[contains(@placeholder, '{field_label}')]")
                field.clear()
                field.send_keys(value)
                time.sleep(1)
            except:
                try:
                    # روش سوم: پیدا کردن با name
                    field_name = field_label.replace(" ", "").replace("‌", "")
                    field = self.driver.find_element(By.NAME, field_name)
                    field.clear()
                    field.send_keys(value)
                    time.sleep(1)
                except Exception as e:
                    logging.warning(f"فیلد {field_label} پیدا نشد: {e}")
    
    def select_dropdown(self, dropdown_label, value):
        """انتخاب از dropdown"""
        try:
            dropdown = self.driver.find_element(By.XPATH, f"//label[contains(text(), '{dropdown_label}')]/following-sibling::select")
            dropdown.click()
            time.sleep(1)
            
            option = dropdown.find_element(By.XPATH, f".//option[contains(text(), '{value}')]")
            option.click()
            time.sleep(1)
        except Exception as e:
            logging.warning(f"Dropdown {dropdown_label} پیدا نشد: {e}")
    
    def check_bank_availability(self, bank_name):
        """بررسی فعال بودن بانک"""
        try:
            bank_urls = {
                'ملی': 'http://ve.cbi.ir/bank/melli',
                'صادرات': 'http://ve.cbi.ir/bank/saderat',
            }
            
            url = bank_urls.get(bank_name, 'http://ve.cbi.ir')
            self.driver.get(url)
            time.sleep(5)
            
            # بررسی وجود فرم
            forms = self.driver.find_elements(By.TAG_NAME, 'form')
            buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'ثبت')]")
            
            is_active = len(forms) > 0 or len(buttons) > 0
            logging.info(f"وضعیت بانک {bank_name}: فعال={is_active}")
            
            return is_active
            
        except Exception as e:
            logging.error(f"خطا در بررسی بانک {bank_name}: {e}")
            return False

class ChildLoanBot:
    def __init__(self):
        self.db = UserDatabase()
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.automation = ChildLoanAutomation(self.application)
        self.setup_handlers()
        
        # شروع مانیتورینگ
        asyncio.create_task(self.start_24_7_monitoring())
    
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
                VERIFICATION_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_verification_code)],
            },
            fallbacks=[CommandHandler('cancel', self.cancel)]
        )
        
        self.application.add_handler(conv_handler)
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.application.add_handler(CommandHandler('status', self.check_status))
        self.application.add_handler(CommandHandler('report', self.get_report))
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "👋 به ربات **اتوماسیون وام قرض الحسنه فرزند** خوش آمدید!\n\n"
            "🤖 این ربات به صورت 24/7:\n"
            "• سامانه بانک‌ها رو بررسی می‌کنه\n"
            "• فرم‌ها رو هوشمند پر می‌کنه\n"  
            "• عکس از تمام مراحل براتون می‌فرسته\n"
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
    
    async def get_parents_status(self, update: Update, context: ContextT
