# ملف إدارة نظام البوتات - ZAKARIA (الإصدار الديناميكي)
# الشمقمق

import multiprocessing
from multiprocessing import Manager
import subprocess
import os
import time
import asyncio
import httpx
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import urllib3
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import json
import sys
import zipfile
import shutil
from pathlib import Path

# مكتبات تليجرام
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# تعطيل التحذيرات المتعلقة بشهادات SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ═══════════════════════════════════════════════════════════════
# الإعدادات الرئيسية
# ═══════════════════════════════════════════════════════════════

TELEGRAM_BOT_TOKEN = "تكون الشمقمق هنا"
ADMIN_IDS = [ايدي الشمقمق]

# ملفات التكوين
CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
ACCOUNT_FILE = os.path.join(CACHE_DIR, "ff_accounts.json")
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
BOTS_CONFIG_FILE = os.path.join(CACHE_DIR, "bots_config.json")

RESTART_INTERVAL = 1800

# ═══════════════════════════════════════════════════════════════
# إعدادات الحد الأقصى للطلبات (Free Fire API)
# ═══════════════════════════════════════════════════════════════

MAX_CONCURRENT_REQUESTS = 2
DELAY_BETWEEN_REQUESTS = 1.5
MAX_RETRIES = 3
RETRY_DELAY = 2
REQUEST_TIMEOUT = 60

# ═══════════════════════════════════════════════════════════════
# إعدادات Free Fire API
# ═══════════════════════════════════════════════════════════════

GUST = {
    "4314554831": "hkhangcuti_W2XT3_Developer_PLongDevz_1064J"
}

DEFAULT_REGION = "VN"

# إعداد جلسة الطلبات
retry_strategy = Retry(
    total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504], allowed_methods=["GET", "POST"],
)
session = requests.Session()
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)
session.mount("http://", adapter)

# ═══════════════════════════════════════════════════════════════
# المتغيرات العامة
# ═══════════════════════════════════════════════════════════════

bot_processes = {}          # المفتاح: اسم المجلد (مثل "bot1")
bot_subprocesses = {}       # المفتاح: اسم المجلد

# ═══════════════════════════════════════════════════════════════
# إنشاء المجلدات
# ═══════════════════════════════════════════════════════════════

def ensure_cache_dir():
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
        print(f"✅ تم إنشاء مجلد التخزين المؤقت: {CACHE_DIR}")

def ensure_log_dir():
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
        print(f"✅ تم إنشاء مجلد السجلات: {LOG_DIR}")

# ═══════════════════════════════════════════════════════════════
# إدارة الحسابات (Free Fire)
# ═══════════════════════════════════════════════════════════════

def load_accounts():
    global GUST
    try:
        ensure_cache_dir()
        if os.path.exists(ACCOUNT_FILE):
            with open(ACCOUNT_FILE, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
                if loaded_data:
                    GUST = loaded_data
                    print(f"✅ تم تحميل {len(GUST)} حساب بنجاح.")
    except Exception as e:
        print(f"❌ خطأ أثناء تحميل الحسابات: {e}")

def save_accounts():
    try:
        ensure_cache_dir()
        with open(ACCOUNT_FILE, 'w', encoding='utf-8') as f:
            json.dump(GUST, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ خطأ أثناء حفظ الحسابات: {e}")
        return False

load_accounts()

# ═══════════════════════════════════════════════════════════════
# إدارة البوتات الديناميكية
# ═══════════════════════════════════════════════════════════════

def load_bots_config():
    """تحميل قائمة البوتات المسجلة من ملف JSON"""
    if not os.path.exists(BOTS_CONFIG_FILE):
        return []
    try:
        with open(BOTS_CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_bots_config(bots_list):
    """حفظ قائمة البوتات في ملف JSON"""
    ensure_cache_dir()
    with open(BOTS_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(bots_list, f, indent=4, ensure_ascii=False)

def get_next_bot_folder():
    """إيجاد أول اسم مجلد غير مستخدم (bot1, bot2, ...)"""
    existing = [p.name for p in Path('.').glob('bot*') if p.is_dir()]
    max_num = 0
    for folder in existing:
        try:
            num = int(folder[3:])
            if num > max_num:
                max_num = num
        except:
            continue
    return f"bot{max_num+1}"

def extract_and_setup_bot(zip_file_path):
    """
    فك ضغط الملف في مجلد جديد وإرجاع (اسم_المجلد, الملف_الرئيسي)
    أو (None, سبب_الفشل) في حال الفشل.
    """
    new_folder = get_next_bot_folder()
    try:
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(new_folder)
        # البحث عن main.py (يمكن تعديل لاحقاً للبحث عن أي ملف .py)
        main_file = None
        for root, dirs, files in os.walk(new_folder):
            if 'main.py' in files:
                main_file = os.path.join(root, 'main.py')
                break
        if not main_file:
            shutil.rmtree(new_folder)
            return None, "لم يتم العثور على main.py"
        # الملف الرئيسي بالنسبة للمجلد
        main_file_rel = os.path.relpath(main_file, new_folder)
        return new_folder, main_file_rel
    except Exception as e:
        if os.path.exists(new_folder):
            shutil.rmtree(new_folder)
        return None, str(e)

# ═══════════════════════════════════════════════════════════════
# دوال التشفير و JWT (Free Fire)
# ═══════════════════════════════════════════════════════════════

def Encrypt_ID(x):
    dec = ['80', '81', '82', '83', '84', '85', '86', '87', '88', '89', '8a', '8b', '8c', '8d', '8e', '8f', '90', '91',
           '92', '93', '94', '95', '96', '97', '98', '99', '9a', '9b', '9c', '9d', '9e', '9f', 'a0', 'a1', 'a2', 'a3',
           'a4', 'a5', 'a6', 'a7', 'a8', 'a9', 'aa', 'ab', 'ac', 'ad', 'ae', 'af', 'b0', 'b1', 'b2', 'b3', 'b4', 'b5',
           'b6', 'b7', 'b8', 'b9', 'ba', 'bb', 'bc', 'bd', 'be', 'bf', 'c0', 'c1', 'c2', 'c3', 'c4', 'c5', 'c6', 'c7',
           'c8', 'c9', 'ca', 'cb', 'cc', 'cd', 'ce', 'cf', 'd0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7', 'd8', 'd9',
           'da', 'db', 'dc', 'dd', 'de', 'df', 'e0', 'e1', 'e2', 'e3', 'e4', 'e5', 'e6', 'e7', 'e8', 'e9', 'ea', 'eb',
           'ec', 'ed', 'ee', 'ef', 'f0', 'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'fa', 'fb', 'fc', 'fd',
           'fe', 'ff']
    xxx = ['1', '01', '02', '03', '04', '05', '06', '07', '08', '09', '0a', '0b', '0c', '0d', '0e', '0f', '10', '11',
           '12', '13', '14', '15', '16', '17', '18', '19', '1a', '1b', '1c', '1d', '1e', '1f', '20', '21', '22', '23',
           '24', '25', '26', '27', '28', '29', '2a', '2b', '2c', '2d', '2e', '2f', '30', '31', '32', '33', '34', '35',
           '36', '37', '38', '39', '3a', '3b', '3c', '3d', '3e', '3f', '40', '41', '42', '43', '44', '45', '46', '47',
           '48', '49', '4a', '4b', '4c', '4d', '4e', '4f', '50', '51', '52', '53', '54', '55', '56', '57', '58', '59',
           '5a', '5b', '5c', '5d', '5e', '5f', '60', '61', '62', '63', '64', '65', '66', '67', '68', '69', '6a', '6b',
           '6c', '6d', '6e', '6f', '70', '71', '72', '73', '74', '75', '76', '77', '78', '79', '7a', '7b', '7c', '7d',
           '7e', '7f']
    try:
        x = int(x)
        x_float = float(x) / 128
        if x_float > 128:
            x_float /= 128
            if x_float > 128:
                x_float /= 128
                if x_float > 128:
                    x_float /= 128
                    strx = int(x_float)
                    y = (x_float - strx) * 128
                    z = (y - int(y)) * 128
                    n = (z - int(z)) * 128
                    m = (n - int(n)) * 128
                    return dec[int(m)] + dec[int(n)] + dec[int(z)] + dec[int(y)] + xxx[int(x_float)]
                else:
                    strx = int(x_float)
                    y = (x_float - strx) * 128
                    z = (y - int(y)) * 128
                    n = (z - int(z)) * 128
                    return dec[int(n)] + dec[int(z)] + dec[int(y)] + xxx[int(x_float)]
        return None
    except Exception:
        return None

def encrypt_api(plain_text):
    key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
    iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return cipher.encrypt(pad(bytes.fromhex(plain_text), AES.block_size)).hex()

def get_jwt(uid, password):
    api_url = f"https://jwt-gen-api-v2.onrender.com/token?uid={uid}&password={password}"
    for attempt in range(MAX_RETRIES):
        try:
            response = session.get(api_url, verify=False, timeout=30)
            if response.status_code == 200:
                data = response.json()
                token = data.get("token")
                if token:
                    return token
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
        except Exception as e:
            print(f"❌ خطأ في استرجاع JWT (المحاولة {attempt + 1}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
    return None

# ═══════════════════════════════════════════════════════════════
# إضافة صديق مع إعادة المحاولة (Free Fire)
# ═══════════════════════════════════════════════════════════════

async def async_add_fr_with_retry(target_id, token, uid, semaphore, client):
    url = 'https://clientbp.ggwhitehawk.com/RequestAddingFriend'
    headers = {
        'X-Unity-Version': '2018.4.11f1',
        'ReleaseVersion': 'OB51',
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-GA': 'v1 1',
        'Authorization': f'Bearer {token}',
        'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 7.1.2; ASUS_Z01QD Build/QKQ1.190825.002)',
        'Host': 'clientbp.ggwhitehawk.com',
        'Connection': 'Keep-Alive',
        'Accept-Encoding': 'gzip'
    }
    encrypted_id = Encrypt_ID(target_id)
    if not encrypted_id:
        return {'status': 'فشل', 'error': 'فشل التشفير', 'uid': uid, 'attempts': 0}

    plain_text_payload = f'08a7c4839f1e10{encrypted_id}1801'
    data = bytes.fromhex(encrypt_api(plain_text_payload))

    async with semaphore:
        for attempt in range(MAX_RETRIES):
            try:
                if attempt > 0:
                    await asyncio.sleep(RETRY_DELAY)
                response = await client.post(url, headers=headers, content=data, timeout=REQUEST_TIMEOUT)
                if response.status_code == 200:
                    return {'status': 'نجاح', 'uid': uid, 'attempts': attempt + 1}
                elif response.status_code == 429:
                    await asyncio.sleep(RETRY_DELAY * 3)
                    continue
                else:
                    if attempt < MAX_RETRIES - 1:
                        continue
                    return {'status': 'فشل', 'error': f'HTTP {response.status_code}', 'uid': uid, 'attempts': attempt + 1}
            except httpx.TimeoutException:
                if attempt < MAX_RETRIES - 1: continue
                return {'status': 'خطأ', 'error': 'انتهاء المهلة', 'uid': uid, 'attempts': attempt + 1}
            except Exception as e:
                if attempt < MAX_RETRIES - 1: continue
                return {'status': 'خطأ', 'error': str(e)[:30], 'uid': uid, 'attempts': attempt + 1}
        return {'status': 'فشل', 'error': 'تجاوز الحد الأقصى للمحاولات', 'uid': uid, 'attempts': MAX_RETRIES}

async def async_add_fr_single(target_id, token, uid):
    semaphore = asyncio.Semaphore(1)
    async with httpx.AsyncClient(verify=False) as client:
        return await async_add_fr_with_retry(target_id, token, uid, semaphore, client)

# ═══════════════════════════════════════════════════════════════
# تغيير البايو مع إعادة المحاولة (Free Fire)
# ═══════════════════════════════════════════════════════════════

async def async_change_bio_with_retry(uid, password, new_bio, region, semaphore, client):
    import urllib.parse
    encoded_bio = urllib.parse.quote(new_bio)
    url = f"https://change-bio-api-lkteam.onrender.com/changebio?uid={uid}&password={password}&newbio={encoded_bio}&region={region}"
    async with semaphore:
        for attempt in range(MAX_RETRIES):
            try:
                if attempt > 0:
                    await asyncio.sleep(RETRY_DELAY)
                response = await client.get(url, timeout=90)
                if response.status_code == 200:
                    return {'status': 'نجاح', 'uid': uid, 'attempts': attempt + 1}
                elif response.status_code == 429:
                    await asyncio.sleep(RETRY_DELAY * 3)
                    continue
                else:
                    if attempt < MAX_RETRIES - 1: continue
                    return {'status': 'فشل', 'error': f'HTTP {response.status_code}', 'uid': uid, 'attempts': attempt + 1}
            except httpx.TimeoutException:
                if attempt < MAX_RETRIES - 1: continue
                return {'status': 'خطأ', 'error': 'انتهاء المهلة', 'uid': uid, 'attempts': attempt + 1}
            except Exception as e:
                if attempt < MAX_RETRIES - 1: continue
                return {'status': 'خطأ', 'error': str(e)[:30], 'uid': uid, 'attempts': attempt + 1}
        return {'status': 'فشل', 'error': 'تجاوز الحد الأقصى للمحاولات', 'uid': uid, 'attempts': MAX_RETRIES}

async def async_change_bio_single(uid, password, new_bio, region):
    semaphore = asyncio.Semaphore(1)
    async with httpx.AsyncClient(verify=False) as client:
        return await async_change_bio_with_retry(uid, password, new_bio, region, semaphore, client)

# ═══════════════════════════════════════════════════════════════
# تشغيل بوت واحد (يتم استدعاؤه في عملية منفصلة)
# ═══════════════════════════════════════════════════════════════

def run_single_bot(folder, filename, bot_id, status_dict, stop_event, error_dict):
    """
    bot_id هو اسم المجلد (مثل "bot1")
    """
    ensure_log_dir()
    log_file = os.path.join(LOG_DIR, f"{bot_id}.log")
    while not stop_event.is_set():
        bot_path = os.path.join(folder, filename)
        print(f"[بدء] البوت {bot_id}: {bot_path}")
        try:
            with open(log_file, 'a', encoding='utf-8') as log:
                log.write(f"\n{'='*50}\n")
                log.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] بدء تشغيل البوت {bot_id}\n")
                log.flush()
                process = subprocess.Popen(
                    [sys.executable, filename],
                    cwd=folder,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    bufsize=1,
                    universal_newlines=True
                )
                bot_subprocesses[bot_id] = process
                time.sleep(5)
                if process.poll() is not None:
                    exit_code = process.returncode
                    error_msg = f"البوت توقف برمز الخروج {exit_code}"
                    error_dict[bot_id] = error_msg
                    status_dict[bot_id] = False
                    print(f"[خطأ] البوت {bot_id}: {error_msg}")
                    log.write(f"[خطأ] {error_msg}\n")
                    time.sleep(10)
                    continue
                else:
                    status_dict[bot_id] = True
                    error_dict[bot_id] = ""
                    print(f"[✅] البوت {bot_id} يعمل الآن")
                start_time = time.time()
                while time.time() - start_time < RESTART_INTERVAL:
                    if stop_event.is_set(): break
                    if process.poll() is not None:
                        exit_code = process.returncode
                        error_msg = f"البوت توقف برمز الخروج {exit_code}"
                        error_dict[bot_id] = error_msg
                        status_dict[bot_id] = False
                        print(f"[انهيار] البوت {bot_id}: {error_msg}")
                        log.write(f"[انهيار] {error_msg}\n")
                        break
                    time.sleep(5)
                print(f"[إعادة تشغيل] البوت {bot_id}: {bot_path}")
                log.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] جاري إعادة تشغيل البوت\n")
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except:
                    try: process.kill()
                    except: pass
        except Exception as e:
            error_msg = str(e)
            error_dict[bot_id] = error_msg
            status_dict[bot_id] = False
            print(f"[خطأ] البوت {bot_id}: {e}")
        time.sleep(2)
    status_dict[bot_id] = False
    print(f"[إيقاف] البوت {bot_id}")

def start_bot_process(bot_folder, status_dict, stop_events, error_dict):
    """تشغيل بوت جديد باستخدام اسم المجلد"""
    bots = load_bots_config()
    bot_info = next((b for b in bots if b['folder'] == bot_folder), None)
    if not bot_info:
        return False, f"❌ البوت {bot_folder} غير موجود في القائمة!"
    folder = bot_info['folder']
    filename = bot_info['main_file']
    
    if bot_folder in bot_processes and bot_processes[bot_folder].is_alive():
        return False, f"⚠️ البوت {bot_folder} يعمل بالفعل!"
    
    bot_file = os.path.join(folder, filename)
    if not os.path.exists(bot_file):
        return False, f"❌ الملف غير موجود: {bot_file}"
    
    stop_events[bot_folder] = multiprocessing.Event()
    p = multiprocessing.Process(target=run_single_bot, args=(folder, filename, bot_folder, status_dict, stop_events[bot_folder], error_dict))
    p.start()
    bot_processes[bot_folder] = p
    return True, f"✅ تم تشغيل البوت {bot_folder}: {folder}/{filename}"

def stop_bot_process(bot_folder, status_dict, stop_events):
    """إيقاف بوت"""
    if bot_folder not in bot_processes or not bot_processes[bot_folder].is_alive():
        return False, f"⚠️ البوت {bot_folder} غير مشتغل!"
    if bot_folder in stop_events:
        stop_events[bot_folder].set()
    bot_processes[bot_folder].join(timeout=10)
    if bot_processes[bot_folder].is_alive():
        bot_processes[bot_folder].terminate()
    status_dict[bot_folder] = False
    return True, f"✅ تم إيقاف البوت {bot_folder}"

def restart_bot_process(bot_folder, status_dict, stop_events, error_dict):
    """إعادة تشغيل بوت"""
    if bot_folder in bot_processes and bot_processes[bot_folder].is_alive():
        if bot_folder in stop_events:
            stop_events[bot_folder].set()
        bot_processes[bot_folder].join(timeout=5)
        if bot_processes[bot_folder].is_alive():
            bot_processes[bot_folder].terminate()
            bot_processes[bot_folder].join(timeout=3)
    time.sleep(2)
    return start_bot_process(bot_folder, status_dict, stop_events, error_dict)

# ═══════════════════════════════════════════════════════════════
# معالجات تليجرام
# ═══════════════════════════════════════════════════════════════

def is_admin(user_id):
    return user_id in ADMIN_IDS

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ أنت لست لديك صلاحية!")
        return
    help_text = """
🤖 *مدير نظام البوتات - الشمقمق (النسخة الديناميكية)*
━━━━━━━━━━━━━━━━━━━━━
📋 *إدارة البوتات:*
• `/on [اسم_المجلد]` - تشغيل بوت
• `/off [اسم_المجلد]` - إيقاف بوت
• `/rs [اسم_المجلد]` - إعادة تشغيل بوت
• `/onall` - تشغيل الكل
• `/offall` - إيقاف الكل
• `/restart` - إعادة تشغيل الكل
• `/status` - حالة البوتات
• `/log [اسم_المجلد]` - عرض السجل
• `/listbots` - قائمة البوتات المسجلة
• `/addbot` - لاستقبال ملف ZIP لإضافة بوت جديد (سيرسل البوت طلب الملف)
• `/delbot [اسم_المجلد]` - حذف بوت
━━━━━━━━━━━━━━━━━━━━━
🎮 *Free Fire:*
• `/kb [id] [رقم]` - إضافة صديق
• `/bio [نص] [رقم]` - تغيير البايو
• `/kball [id]` - إضافة للكل
• `/bioall [نص]` - بايو للكل
━━━━━━━━━━━━━━━━━━━━━
⚙️ *الحسابات:*
• `/addacc [uid]|[pass]` - إضافة
• `/listacc` - قائمة
• `/delacc [uid]` - حذف
• `/clearacc` - حذف الكل
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def cmd_addbot_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يطلب من المستخدم إرسال ملف ZIP لإضافة بوت جديد"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ ليس لديك صلاحية!")
        return

    # تخزين حالة انتظار الملف للمستخدم
    context.user_data['waiting_for_bot_zip'] = True
    await update.message.reply_text("📦 أرسل ملف ZIP الذي يحتوي على `main.py` (الملف الرئيسي للبوت).", parse_mode='Markdown')

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الملفات المرسلة بعد طلب /addbot"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ ليس لديك صلاحية!")
        return

    # التحقق من أن المستخدم في حالة انتظار الملف
    if not context.user_data.get('waiting_for_bot_zip', False):
        # إذا لم يكن ينتظر ملفاً، نهمل
        return

    # مسح حالة الانتظار
    context.user_data['waiting_for_bot_zip'] = False

    document = update.message.document
    if not document or not document.file_name.endswith('.zip'):
        await update.message.reply_text("❗ يرجى إرسال ملف بصيغة ZIP فقط.")
        return

    # تحميل الملف
    await update.message.reply_text("⏳ جاري تحميل الملف...")
    file = await context.bot.get_file(document.file_id)
    temp_zip = os.path.join(CACHE_DIR, f"temp_{document.file_id}.zip")
    await file.download_to_drive(temp_zip)

    # فك الضغط وإعداد البوت
    await update.message.reply_text("⏳ جاري فك الضغط وإعداد البوت...")
    folder, main_file = extract_and_setup_bot(temp_zip)
    os.remove(temp_zip)

    if not folder:
        await update.message.reply_text(f"❌ فشل في إعداد البوت: {main_file}")
        return

    # إضافة البوت إلى القائمة
    bots = load_bots_config()
    new_bot = {
        "folder": folder,
        "main_file": main_file,
        "added_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    bots.append(new_bot)
    save_bots_config(bots)

    # تشغيل البوت الجديد
    status_dict = context.bot_data.get('status_dict')
    stop_events = context.bot_data.get('stop_events')
    error_dict = context.bot_data.get('error_dict')
    success, msg = start_bot_process(folder, status_dict, stop_events, error_dict)

    await update.message.reply_text(f"✅ تمت إضافة البوت `{folder}`\n📁 {folder}\n🔧 {main_file}\n{msg}", parse_mode='Markdown')

async def cmd_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ ليس لديك صلاحية!")
        return
    if not context.args:
        await update.message.reply_text("❗ `/on [اسم_المجلد]`", parse_mode='Markdown')
        return
    bot_folder = context.args[0]
    status_dict = context.bot_data.get('status_dict')
    stop_events = context.bot_data.get('stop_events')
    error_dict = context.bot_data.get('error_dict')
    success, msg = start_bot_process(bot_folder, status_dict, stop_events, error_dict)
    await update.message.reply_text(msg)
    if success:
        await asyncio.sleep(5)
        error = error_dict.get(bot_folder, "")
        if error:
            await update.message.reply_text(f"⚠️ البوت {bot_folder} قد توقف!\n{error}", parse_mode='Markdown')

async def cmd_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id): return
    if not context.args:
        await update.message.reply_text("❗ `/off [اسم_المجلد]`", parse_mode='Markdown')
        return
    bot_folder = context.args[0]
    status_dict = context.bot_data.get('status_dict')
    stop_events = context.bot_data.get('stop_events')
    success, msg = stop_bot_process(bot_folder, status_dict, stop_events)
    await update.message.reply_text(msg)

async def cmd_rs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id): return
    if not context.args:
        await update.message.reply_text("❗ `/rs [اسم_المجلد]`", parse_mode='Markdown')
        return
    bot_folder = context.args[0]
    status_dict = context.bot_data.get('status_dict')
    stop_events = context.bot_data.get('stop_events')
    error_dict = context.bot_data.get('error_dict')
    await update.message.reply_text(f"🔄 جاري إعادة تشغيل البوت {bot_folder}...")
    success, msg = restart_bot_process(bot_folder, status_dict, stop_events, error_dict)
    await update.message.reply_text(msg)

async def cmd_onall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id): return
    status_dict = context.bot_data.get('status_dict')
    stop_events = context.bot_data.get('stop_events')
    error_dict = context.bot_data.get('error_dict')
    bots = load_bots_config()
    await update.message.reply_text("🚀 جاري تشغيل كل البوتات...")
    results = []
    for bot in bots:
        bot_folder = bot['folder']
        success, msg = start_bot_process(bot_folder, status_dict, stop_events, error_dict)
        results.append(f"{'✅' if success else '⚠️'} {bot_folder}")
        await asyncio.sleep(1)
    await update.message.reply_text(f"🚀 *النتيجة:*\n" + "\n".join(results), parse_mode='Markdown')

async def cmd_offall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id): return
    status_dict = context.bot_data.get('status_dict')
    stop_events = context.bot_data.get('stop_events')
    bots = load_bots_config()
    await update.message.reply_text("🛑 جاري إيقاف كل البوتات...")
    results = []
    for bot in bots:
        bot_folder = bot['folder']
        success, msg = stop_bot_process(bot_folder, status_dict, stop_events)
        results.append(f"{'✅' if success else '⚠️'} {bot_folder}")
    await update.message.reply_text(f"🛑 *النتيجة:*\n" + "\n".join(results), parse_mode='Markdown')

async def cmd_restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id): return
    status_dict = context.bot_data.get('status_dict')
    stop_events = context.bot_data.get('stop_events')
    error_dict = context.bot_data.get('error_dict')
    bots = load_bots_config()
    await update.message.reply_text("🔄 جاري إعادة تشغيل كل البوتات...")
    results = []
    success_count = 0
    for bot in bots:
        bot_folder = bot['folder']
        success, msg = restart_bot_process(bot_folder, status_dict, stop_events, error_dict)
        if success:
            success_count += 1
            results.append(f"✅ {bot_folder}")
        else:
            results.append(f"❌ {bot_folder}")
        await asyncio.sleep(2)
    await update.message.reply_text(f"🔄 *تمت إعادة التشغيل!*\n🟢 نجح: {success_count}/{len(bots)}\n" + "\n".join(results), parse_mode='Markdown')

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id): return
    status_dict = context.bot_data.get('status_dict', {})
    error_dict = context.bot_data.get('error_dict', {})
    bots = load_bots_config()
    running_count = 0
    status_text = "📊 *حالة البوتات*\n━━━━━━━━━━━━━━━━━━━━━\n"
    for bot in bots:
        bot_folder = bot['folder']
        proc_alive = bot_folder in bot_processes and bot_processes[bot_folder].is_alive()
        is_running = proc_alive and status_dict.get(bot_folder, False)
        error = error_dict.get(bot_folder, "")
        if is_running and not error:
            running_count += 1
            status = "🟢 Online"
        elif proc_alive and error:
            status = "🟡 Crashed"
        elif proc_alive:
            status = "🟡 Starting..."
        else:
            status = "🔴 Offline"
        status_text += f"`{bot_folder}`: {status}\n"
        if error:
            status_text += f"   └ _{error[:40]}_\n"
    status_text += f"\n━━━━━━━━━━━━━━━━━━━━━\n📈 *متصل:* {running_count}/{len(bots)}"
    await update.message.reply_text(status_text, parse_mode='Markdown')

async def cmd_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id): return
    if not context.args:
        await update.message.reply_text("❗ `/log [اسم_المجلد]`", parse_mode='Markdown')
        return
    bot_folder = context.args[0]
    log_file = os.path.join(LOG_DIR, f"{bot_folder}.log")
    if not os.path.exists(log_file):
        await update.message.reply_text(f"📄 لا يوجد سجل للبوت {bot_folder}")
        return
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
        last_lines = lines[-50:] if len(lines) > 50 else lines
        log_content = "".join(last_lines)
    if len(log_content) > 3500:
        log_content = log_content[-3500:]
    await update.message.reply_text(f"📄 *سجل البوت {bot_folder}* (آخر 50 سطر)\n```\n{log_content}\n```", parse_mode='Markdown')

async def cmd_listbots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id): return
    bots = load_bots_config()
    if not bots:
        await update.message.reply_text("📋 لا توجد بوتات مسجلة.")
        return
    list_text = "📋 *قائمة البوتات المسجلة*\n━━━━━━━━━━━━━━━━━━━━━\n"
    for i, bot in enumerate(bots, 1):
        status = "🟢 يعمل" if (bot['folder'] in bot_processes and bot_processes[bot['folder']].is_alive()) else "🔴 متوقف"
        list_text += f"{i}. `{bot['folder']}` - {status}\n"
    await update.message.reply_text(list_text, parse_mode='Markdown')

async def cmd_delbot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ ليس لديك صلاحية!")
        return
    if not context.args:
        await update.message.reply_text("❗ /delbot [اسم_المجلد]")
        return
    bot_folder = context.args[0]

    bots = load_bots_config()
    bot_info = next((b for b in bots if b['folder'] == bot_folder), None)
    if not bot_info:
        await update.message.reply_text(f"❌ البوت {bot_folder} غير موجود!")
        return

    # إيقاف البوت إن كان يعمل
    status_dict = context.bot_data.get('status_dict')
    stop_events = context.bot_data.get('stop_events')
    if bot_folder in bot_processes and bot_processes[bot_folder].is_alive():
        stop_bot_process(bot_folder, status_dict, stop_events)

    # حذف مجلد البوت
    folder_path = bot_info['folder']
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)

    # إزالة من القائمة
    bots = [b for b in bots if b['folder'] != bot_folder]
    save_bots_config(bots)

    await update.message.reply_text(f"✅ تم حذف البوت {bot_folder} ومجلده {folder_path}")

# ═══════════════════════════════════════════════════════════════
# أوامر Free Fire (نفسها كما هي)
# ═══════════════════════════════════════════════════════════════

async def cmd_kb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id): return
    if len(context.args) < 2:
        await update.message.reply_text("❗ `/kb [id] [رقم]`", parse_mode='Markdown')
        return
    try:
        target_id = context.args[0]
        acc_index = int(context.args[1])
        if not target_id.isdigit():
            await update.message.reply_text("❗ الـ ID يجب أن يكون رقمًا!")
            return
        accounts_list = list(GUST.items())
        if acc_index < 1 or acc_index > len(accounts_list):
            await update.message.reply_text(f"❗ رقم الحساب غير صحيح! (1-{len(accounts_list)})")
            return
        uid, password = accounts_list[acc_index - 1]
        await update.message.reply_text(f"⏳ جاري إضافة الصديق...\n🆔 من: `{uid}`\n🎯 إلى: `{target_id}`", parse_mode='Markdown')
        token = get_jwt(uid, password)
        if not token:
            await update.message.reply_text("❌ فشل في الحصول على التوكن!")
            return
        result = await async_add_fr_single(target_id, token, uid)
        if result.get('status') == 'نجاح':
            await update.message.reply_text(f"✅ *تمت إضافة الصديق بنجاح!*\n🆔 `{uid}` → `{target_id}`", parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ فشل: {result.get('error', 'غير معروف')}")
    except ValueError:
        await update.message.reply_text("❗ الرقم يجب أن يكون رقمًا!")

async def cmd_kball(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id): return
    if not context.args:
        await update.message.reply_text("❗ `/kball [id]`", parse_mode='Markdown')
        return
    target_id = context.args[0]
    if not target_id.isdigit():
        await update.message.reply_text("❗ الـ ID يجب أن يكون رقمًا!")
        return
    if not GUST:
        await update.message.reply_text("❌ لا توجد حسابات!")
        return
    await update.message.reply_text(f"⏳ جاري إضافة الصديق لكل الحسابات...\n🎯 `{target_id}`\n📊 عدد الحسابات: {len(GUST)}", parse_mode='Markdown')
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    results = []
    async with httpx.AsyncClient(verify=False) as client:
        for i, (uid, password) in enumerate(GUST.items(), 1):
            if i > 1: await asyncio.sleep(DELAY_BETWEEN_REQUESTS)
            token = get_jwt(uid, password)
            if not token:
                results.append({'status': 'فشل', 'error': 'Token', 'uid': uid})
                continue
            result = await async_add_fr_with_retry(target_id, token, uid, semaphore, client)
            results.append(result)
    success_count = sum(1 for r in results if r.get('status') == 'نجاح')
    await update.message.reply_text(f"✅ *انتهى!*\n🟢 نجح: {success_count} | 🔴 فشل: {len(results)-success_count}", parse_mode='Markdown')

async def cmd_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id): return
    if len(context.args) < 2:
        await update.message.reply_text("❗ `/bio [النص] [رقم]`", parse_mode='Markdown')
        return
    try:
        acc_index = int(context.args[-1])
        new_bio = " ".join(context.args[:-1])
        accounts_list = list(GUST.items())
        if acc_index < 1 or acc_index > len(accounts_list):
            await update.message.reply_text(f"❗ رقم الحساب غير صحيح! (1-{len(accounts_list)})")
            return
        uid, password = accounts_list[acc_index - 1]
        await update.message.reply_text(f"⏳ جاري تغيير البايو...\n🆔 `{uid}`\n📝 {new_bio}", parse_mode='Markdown')
        result = await async_change_bio_single(uid, password, new_bio, DEFAULT_REGION)
        if result.get('status') == 'نجاح':
            await update.message.reply_text(f"✅ *تم تغيير البايو بنجاح!*\n📝 {new_bio}", parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ فشل: {result.get('error')}")
    except ValueError:
        await update.message.reply_text("❗ الرقم في النهاية يجب أن يكون رقمًا!")

async def cmd_bioall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id): return
    if not context.args:
        await update.message.reply_text("❗ `/bioall [النص]`", parse_mode='Markdown')
        return
    new_bio = " ".join(context.args)
    if not GUST:
        await update.message.reply_text("❌ لا توجد حسابات!")
        return
    await update.message.reply_text(f"⏳ جاري تغيير البايو لكل الحسابات...\n📝 {new_bio}\n📊 {len(GUST)} حساب", parse_mode='Markdown')
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    results = []
    async with httpx.AsyncClient(verify=False) as client:
        for i, (uid, password) in enumerate(GUST.items(), 1):
            if i > 1: await asyncio.sleep(DELAY_BETWEEN_REQUESTS)
            result = await async_change_bio_with_retry(uid, password, new_bio, DEFAULT_REGION, semaphore, client)
            results.append(result)
    success_count = sum(1 for r in results if r.get('status') == 'نجاح')
    await update.message.reply_text(f"📝 *انتهى!*\n🟢 نجح: {success_count} | 🔴 فشل: {len(results)-success_count}", parse_mode='Markdown')

# ═══════════════════════════════════════════════════════════════
# إدارة الحسابات (Free Fire)
# ═══════════════════════════════════════════════════════════════

async def cmd_addacc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id): return
    if not context.args:
        await update.message.reply_text("❗ `/addacc [uid]|[password]`", parse_mode='Markdown')
        return
    account_info = " ".join(context.args)
    if "|" not in account_info:
        await update.message.reply_text("❗ استخدم التنسيق: uid|password")
        return
    parts = account_info.split("|", 1)
    uid = parts[0].strip()
    password = parts[1].strip()
    if not uid.isdigit():
        await update.message.reply_text("❗ UID يجب أن يكون رقمًا!")
        return
    await update.message.reply_text(f"⏳ جاري التحقق من الحساب `{uid}`...", parse_mode='Markdown')
    token = get_jwt(uid, password)
    if token:
        GUST[uid] = password
        save_accounts()
        await update.message.reply_text(f"✅ *تمت إضافة الحساب بنجاح!*\n🆔 `{uid}`\n📊 الإجمالي: {len(GUST)}", parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ التوكن غير صالح!")

async def cmd_listacc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id): return
    if not GUST:
        await update.message.reply_text("📋 القائمة فارغة!")
        return
    list_text = f"📋 *الحسابات ({len(GUST)})*\n━━━━━━━━━━━━━━━━━━━━━\n"
    for i, (uid, _) in enumerate(GUST.items(), 1):
        list_text += f"{i}. `{uid}`\n"
    await update.message.reply_text(list_text, parse_mode='Markdown')

async def cmd_delacc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id): return
    if not context.args:
        await update.message.reply_text("❗ `/delacc [uid]`", parse_mode='Markdown')
        return
    uid = context.args[0].strip()
    if uid in GUST:
        del GUST[uid]
        save_accounts()
        await update.message.reply_text(f"✅ تم حذف `{uid}`")
    else:
        await update.message.reply_text("❌ الحساب غير موجود!")

async def cmd_clearacc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id): return
    count = len(GUST)
    GUST.clear()
    save_accounts()
    await update.message.reply_text(f"✅ تم حذف {count} حساب!")

# ═══════════════════════════════════════════════════════════════
# تشغيل بوت تليجرام
# ═══════════════════════════════════════════════════════════════

def run_telegram_bot(status_dict, stop_events, error_dict):
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.bot_data['status_dict'] = status_dict
    app.bot_data['stop_events'] = stop_events
    app.bot_data['error_dict'] = error_dict

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_start))
    app.add_handler(CommandHandler("on", cmd_on))
    app.add_handler(CommandHandler("off", cmd_off))
    app.add_handler(CommandHandler("rs", cmd_rs))
    app.add_handler(CommandHandler("restart", cmd_restart))
    app.add_handler(CommandHandler("onall", cmd_onall))
    app.add_handler(CommandHandler("offall", cmd_offall))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("log", cmd_log))
    app.add_handler(CommandHandler("listbots", cmd_listbots))
    app.add_handler(CommandHandler("addbot", cmd_addbot_request))      # أمر جديد
    app.add_handler(CommandHandler("delbot", cmd_delbot))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))  # استقبال الملفات
    app.add_handler(CommandHandler("kb", cmd_kb))
    app.add_handler(CommandHandler("kball", cmd_kball))
    app.add_handler(CommandHandler("bio", cmd_bio))
    app.add_handler(CommandHandler("bioall", cmd_bioall))
    app.add_handler(CommandHandler("addacc", cmd_addacc))
    app.add_handler(CommandHandler("listacc", cmd_listacc))
    app.add_handler(CommandHandler("delacc", cmd_delacc))
    app.add_handler(CommandHandler("clearacc", cmd_clearacc))

    print("🤖 تم تشغيل مدير البوتات بنجاح!")
    print(f"📊 يدير {len(load_bots_config())} بوت")
    app.run_polling(drop_pending_updates=True)

# ═══════════════════════════════════════════════════════════════
# الشمقمق
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 بدء النظام - ZAKARIA (Dynamic Hosting)")
    print("=" * 50)
    ensure_cache_dir()
    ensure_log_dir()

    manager = Manager()
    status_dict = manager.dict()
    error_dict = manager.dict()
    stop_events = {}

    # تحميل البوتات المسجلة
    bots = load_bots_config()
    print(f"\n📍 جاري تحميل {len(bots)} بوت مسجل...")

    for bot_info in bots:
        folder = bot_info['folder']
        filename = bot_info['main_file']
        bot_file = os.path.join(folder, filename)
        if not os.path.exists(bot_file):
            print(f"  ⚠️ البوت {folder}: الملف غير موجود في {bot_file}")
            continue
        stop_events[folder] = multiprocessing.Event()
        error_dict[folder] = ""
        p = multiprocessing.Process(target=run_single_bot, args=(folder, filename, folder, status_dict, stop_events[folder], error_dict))
        p.start()
        bot_processes[folder] = p
        print(f"  ✅ البوت {folder}: {folder}/{filename}")

    print(f"\n✅ تم تشغيل {len(bot_processes)} بوت.")
    print("📍 جاري تشغيل بوت تليجرام...")
    time.sleep(5)
    try:
        run_telegram_bot(status_dict, stop_events, error_dict)
    except KeyboardInterrupt:
        print("\n🛑 إيقاف النظام...")
        for ev in stop_events.values():
            ev.set()
        for p in bot_processes.values():
            p.terminate()
        print("👋 وداعاً!")