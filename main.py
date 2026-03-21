# ملف إدارة نظام البوتات - ZAKARIA (الإصدار شمقمق1)
# الشمقمق
#تغيير الحقوق لن يجعل منك محترفا شمقمق عمك
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
import threading
from flask import Flask
from cryptography.hazmat.primitives.ciphers import Cipher as Cp, algorithms as Al, modes as Md
from cryptography.hazmat.backends import default_backend as Bk
from google.protobuf.internal.decoder import _DecodeVarint32
from datetime import datetime

# مكتبات تليجرام
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# تعطيل التحذيرات المتعلقة بشهادات SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ═══════════════════════════════════════════════════════════════
# الإعدادات الرئيسية
# ═══════════════════════════════════════════════════════════════

TELEGRAM_BOT_TOKEN = "8598136584:AAFM_fzQv4x5mWFza_BAYtY_jhN1cXXxbqs"
ADMIN_IDS = [6848455321]

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

GUST = {}  # سيتم تحميلها من الملف
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
        main_file = None
        for root, dirs, files in os.walk(new_folder):
            if 'main.py' in files:
                main_file = os.path.join(root, 'main.py')
                break
        if not main_file:
            shutil.rmtree(new_folder)
            return None, "لم يتم العثور على main.py"
        main_file_rel = os.path.relpath(main_file, new_folder)
        return new_folder, main_file_rel
    except Exception as e:
        if os.path.exists(new_folder):
            shutil.rmtree(new_folder)
        return None, str(e)

# ═══════════════════════════════════════════════════════════════
# دوال التشفير الأساسية (لإضافة الصديق)
# ═══════════════════════════════════════════════════════════════

def encrypt_api(plain_text):
    plain_text = bytes.fromhex(plain_text)
    key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
    iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
    cipher = AES.new(key, AES.MODE_CBC, iv)
    cipher_text = cipher.encrypt(pad(plain_text, AES.block_size))
    return cipher_text.hex()

def Encrypt_ID(number):
    number = int(number)
    encoded_bytes = []
    while True:
        byte = number & 0x7F
        number >>= 7
        if number:
            byte |= 0x80
        encoded_bytes.append(byte)
        if not number:
            break
    return bytes(encoded_bytes).hex()

# ═══════════════════════════════════════════════════════════════
# دوال الحصول على التوكن (جديدة من index.py)
# ═══════════════════════════════════════════════════════════════

# بيانات ثابتة مطلوبة في TOKEN_MAKER
OLD_ACCESS_TOKEN = "c69ae208fad72738b674b2847b50a3a1dfa25d1a19fae745fc76ac4a0e414c94"
OLD_OPEN_ID = "4306245793de86da425a52caadf21eed"

def TOKEN_MAKER(OLD_ACCESS_TOKEN, NEW_ACCESS_TOKEN, OLD_OPEN_ID, NEW_OPEN_ID, uid):
    """صانع التوكن - نفس الموجود في index.py"""
    now = datetime.now()
    now = str(now)[:len(str(now)) - 7]

    data = bytes.fromhex(
        '1a13323032352d31312d32362030313a35313a3238220966726565206669726528013a07312e3132302e314232416e64726f6964204f532039202f204150492d3238202850492f72656c2e636a772e32303232303531382e313134313333294a0848616e6468656c64520c4d544e2f537061636574656c5a045749464960800a68d00572033234307a2d7838362d3634205353453320535345342e3120535345342e32204156582041565832207c2032343030207c20348001e61e8a010f416472656e6f2028544d292036343092010d4f70656e474c20455320332e329a012b476f6f676c657c36323566373136662d393161372d343935622d396631362d303866653964336336353333a2010e3137362e32382e3133392e313835aa01026172b201203433303632343537393364653836646134323561353263616164663231656564ba010134c2010848616e6468656c64ca010d4f6e65506c7573204135303130ea014063363961653230386661643732373338623637346232383437623530613361316466613235643161313966616537343566633736616334613065343134633934f00101ca020c4d544e2f537061636574656cd2020457494649ca03203161633462383065636630343738613434323033626638666163363132306635e003b5ee02e8039a8002f003af13f80384078004a78f028804b5ee029004a78f029804b5ee02b00404c80401d2043d2f646174612f6170702f636f6d2e6474732e667265656669726574682d66705843537068495636644b43376a4c2d574f7952413d3d2f6c69622f61726de00401ea045f65363261623933353464386662356662303831646233333861636233333439317c2f646174612f6170702f636f6d2e6474732e667265656669726574682d66705843537068495636644b43376a4c2d574f7952413d3d2f626173652e61706bf00406f804018a050233329a050a32303139313139303236a80503b205094f70656e474c455332b805ff01c00504e005be7eea05093372645f7061727479f205704b717348543857393347646347335a6f7a454e6646775648746d377171316552554e6149444e67526f626f7a4942744c4f695943633459367a767670634943787a514632734f453463627974774c7334785a62526e70524d706d5752514b6d654f35766373386e51594268777148374bf805e7e4068806019006019a060134a2060134b2062213521146500e590349510e460900115843395f005b510f685b560a6107576d0f0366'
    )

    data = data.replace(OLD_OPEN_ID.encode(), NEW_OPEN_ID.encode())
    data = data.replace(OLD_ACCESS_TOKEN.encode(), NEW_ACCESS_TOKEN.encode())

    encrypted = encrypt_api(data.hex())
    Final_Payload = bytes.fromhex(encrypted)

    headers = {
        'X-Unity-Version': '2018.4.11f1',
        'ReleaseVersion': 'ob52',
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-GA': 'v1 1',
        'Authorization': 'Bearer ...',
        'Content-Length': '928',
        'User-Agent': 'Dalvik/2.1.0',
        'Host': 'loginbp.ggpolarbear.com',
        'Connection': 'Keep-Alive',
        'Accept-Encoding': 'gzip'
    }

    url = "https://loginbp.ggpolarbear.com/MajorLogin"
    response = session.post(url, headers=headers, data=Final_Payload, verify=False)

    if response.status_code == 200:
        if len(response.text) < 10:
            return False

        base = response.text[
            response.text.find("eyJhbGciOiJIUzI1NiIsInN2ciI6IjEiLCJ0eXAiOiJKV1QifQ"):
            -1
        ]

        second_dot = base.find(".", base.find(".") + 1)
        base = base[:second_dot + 44]
        return base
    return False

def get_fresh_token(uid, password):
    """الحصول على JWT اللعبة باستخدام uid و password (نفس index.py)"""
    try:
        # الخطوة 1: الحصول على access_token من Garena
        url = "https://100067.connect.garena.com/oauth/guest/token/grant"
        headers = {
            "Host": "100067.connect.garena.com",
            "User-Agent": "GarenaMSDK/4.0.19P4",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "uid": uid,
            "password": password,
            "response_type": "token",
            "client_type": "2",
            "client_id": "100067",
            "client_secret": ""
        }
        r = session.post(url, headers=headers, data=data, timeout=30)
        if r.status_code != 200:
            print(f"[❌] فشل الاتصال بـ Garena: {r.status_code}")
            return None
        d = r.json()
        NEW_ACCESS_TOKEN = d.get("access_token")
        NEW_OPEN_ID = d.get("open_id")
        if not NEW_ACCESS_TOKEN or not NEW_OPEN_ID:
            print("[❌] لم يتم استلام التوكن من Garena")
            return None
        # الخطوة 2: إنشاء JWT اللعبة باستخدام TOKEN_MAKER
        jwt = TOKEN_MAKER(OLD_ACCESS_TOKEN, NEW_ACCESS_TOKEN, OLD_OPEN_ID, NEW_OPEN_ID, uid)
        return jwt
    except Exception as e:
        print(f"[❌] خطأ في get_fresh_token: {e}")
        return None

def get_jwt(uid, password):
    """الحصول على JWT اللعبة باستخدام uid و password (واجهة موحدة)"""
    return get_fresh_token(uid, password)

# ═══════════════════════════════════════════════════════════════
# دوال تغيير البايو (OB52)
# ═══════════════════════════════════════════════════════════════

K_bio = b"Yg&tc%DEuh6%Zc^8"
IV_bio = b"6oyZDr22E3ychjM%"

def pad_bio(d):
    n = 16 - (len(d) % 16)
    return d + bytes([n] * n)

def unpad_bio(d):
    p = d[-1]
    return d[:-p] if 1 <= p <= 16 else d

def encrypt_bio(b):
    cipher = Cp(Al.AES(K_bio), Md.CBC(IV_bio), backend=Bk())
    encryptor = cipher.encryptor()
    return encryptor.update(pad_bio(b)) + encryptor.finalize()

def decrypt_bio(b):
    cipher = Cp(Al.AES(K_bio), Md.CBC(IV_bio), backend=Bk())
    decryptor = cipher.decryptor()
    return unpad_bio(decryptor.update(b) + decryptor.finalize())

def protobuf_decode(data):
    """فك ترميز رسالة protobuf"""
    i, out = 0, {}
    while i < len(data):
        try:
            key, i = _DecodeVarint32(data, i)
        except:
            break
        fn, wt = key >> 3, key & 0x7
        if wt == 0:
            v, i = _DecodeVarint32(data, i)
            out[str(fn)] = {"t": "int", "v": v}
        elif wt == 2:
            ln, i = _DecodeVarint32(data, i)
            v = data[i:i+ln]
            i += ln
            try:
                out[str(fn)] = {"t": "str", "v": v.decode()}
            except:
                out[str(fn)] = {"t": "hex", "v": v.hex()}
        elif wt == 1:
            out[str(fn)] = {"t": "64b", "v": data[i:i+8].hex()}
            i += 8
        elif wt == 5:
            out[str(fn)] = {"t": "32b", "v": data[i:i+4].hex()}
            i += 4
        else:
            break
    return out

def inspect_token(access_token):
    """التحقق من صحة التوكن وجلب open_id"""
    url = "https://100067.connect.garena.com/oauth/token/inspect"
    headers = {
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "close",
        "Content-Type": "application/x-www-form-urlencoded",
        "Host": "100067.connect.garena.com",
        "User-Agent": "GarenaMSDK/4.0.19P4(G011A ;Android 9;en;US;)",
    }
    r = session.get(url, params={"token": access_token}, headers=headers, timeout=10)
    data = r.json()
    if "error" in data:
        raise Exception(f"token error: {data['error']}")
    return data.get("open_id"), data.get("platform")

def build_login_data(access_token, open_id):
    """بناء البيانات المشفرة لتسجيل الدخول إلى اللعبة"""
    template_hex = (
        "1a13323032352d30372d33302031343a31313a3230220966726565206669726528013a07"
        "322e3131342e324234416e64726f6964204f53203133202f204150492d33332028545031"
        "412e3232303632342e3031342f3235303531355631393737294a0848616e6468656c6452"
        "094f72616e676520544e5a0457494649609c1368b80872033438307a1d41524d3634204650"
        "204153494d4420414553207c2032303030207c20388001973c8a010c4d616c692d473532"
        "204d433292013e4f70656e474c20455320332e322076312e72333270312d3031656163302e"
        "32613839336330346361303032366332653638303264626537643761663563359a012b476f"
        "6f676c657c61326365613833342d353732362d346235622d383666322d373130356364386666"
        "353530a2010e3139362e3138372e3132382e3334aa0102656eb201203965373166616266343364"
        "383863303662373966353438313034633766636237ba010134c2010848616e6468656c64ca0115"
        "494e46494e495820496e66696e6978205836383336ea014063363231663264363231343330646163"
        "316137383261306461623634653663383061393734613662633732386366326536623132323464313836"
        "633962376166f00101ca02094f72616e676520544ed2020457494649ca03203161633462383065636630"
        "343738613434323033626638666163363132306635e003dc810ee803daa106f003ef068004e7a506"
        "8804dc810e9004e7a5069804dc810ec80403d2045b2f646174612f6170702f7e7e73444e524632"
        "526357313830465a4d66624d5a636b773d3d2f636f6d2e6474732e66726565666972656d61782d"
        "4a534d4f476d33464e59454271535376587767495a413d3d2f6c69622f61726d3634e00402ea047b"
        "61393862306265333734326162303061313966393737633637633031633266617c2f646174612f6170"
        "702f7e7e73444e524632526357313830465a4d66624d5a636b773d3d2f636f6d2e6474732e66726565"
        "666972656d61782d4a534d4f476d33464e59454271535376587767495a413d3d2f626173652e61706b"
        "f00402f804028a050236349a050a32303139313135363537a80503b205094f70656e474c455333b805"
        "ff7fc00504d20506526164c3a873da05023133e005b9f601ea050b616e64726f69645f6d6178f2055c"
        "4b71734854346230414a3777466c617231594d4b693653517a6732726b3665764f38334f306f59306763"
        "635a626457467a785633483564454f586a47704e3967476956774b7533547a312b716a36326546673074"
        "627537664350553d8206147b226375725f72617465223a5b36302c39305d7d880601900601"
        "9a060134a2060134b20600"
    )
    data_bytes = bytes.fromhex(template_hex)
    # استبدال الطابع الزمني
    timestamp = str(datetime.now())[:-7].encode()
    data_bytes = data_bytes.replace(b"2025-07-30 14:11:20", timestamp)
    # استبدال access_token و open_id
    data_bytes = data_bytes.replace(b"c621f2d621430dac1a782a0dab64e6c80a974a6bc728cf2e6b1224d186c9b7af", access_token.encode())
    data_bytes = data_bytes.replace(b"9e71fabf43d88c06b79f548104c7fcb7", open_id.encode())
    return encrypt_bio(data_bytes)

def get_game_token(access_token, open_id):
    """الحصول على JWT الخاص باللعبة باستخدام access_token"""
    payload = build_login_data(access_token, open_id)
    url = "https://loginbp.common.ggbluefox.com/MajorLogin"
    headers = {
        "Expect": "100-continue",
        "X-Unity-Version": "2018.4.11f1",
        "X-GA": "v1 1",
        "ReleaseVersion": "OB52",
        "Authorization": "Bearer ",
        "Host": "loginbp.common.ggbluefox.com",
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 13; A063)",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept-Encoding": "gzip",
    }
    r = session.post(url, data=payload, headers=headers, timeout=20)
    if r.status_code != 200:
        raise Exception(f"MajorLogin failed with status {r.status_code}")
    decoded = protobuf_decode(r.content)
    token = decoded.get("8", {}).get("v", "")
    if not token:
        raise Exception("No token in response")
    return token.strip()

def set_bio_with_jwt(jwt, text):
    """تغيير البايو باستخدام JWT"""
    raw = b"\x10\x11\x42" + bytes([len(text.encode())]) + text.encode() + b"\x48\x01"
    url = "https://clientbp.ggpolarbear.com/UpdateSocialBasicInfo"
    headers = {
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 13; A063 Build/TKQ1.221220.001)",
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip",
        "Expect": "100-continue",
        "Authorization": f"Bearer {jwt}",
        "X-Unity-Version": "2018.4.11f1",
        "X-GA": "v1 1",
        "ReleaseVersion": "OB52",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    r = session.post(url, data=encrypt_bio(raw), headers=headers, timeout=15)
    return r.status_code

def change_bio_sync(uid, password, new_bio):
    """تغيير البايو باستخدام uid/password"""
    jwt = get_jwt(uid, password)  # JWT اللعبة مباشرة
    if not jwt:
        return {'status': 'فشل', 'error': 'فشل في الحصول على JWT', 'uid': uid}
    try:
        status = set_bio_with_jwt(jwt, new_bio)
        if status == 200:
            return {'status': 'نجاح', 'uid': uid}
        else:
            return {'status': 'فشل', 'error': f'HTTP {status}', 'uid': uid}
    except Exception as e:
        return {'status': 'خطأ', 'error': str(e)[:50], 'uid': uid}

# ═══════════════════════════════════════════════════════════════
# إضافة صديق مع إعادة المحاولة (OB52)
# ═══════════════════════════════════════════════════════════════

async def async_add_fr_with_retry(target_id, token, uid, semaphore, client):
    url = 'https://clientbp.ggpolarbear.com/RequestAddingFriend'
    headers = {
        'X-Unity-Version': '2018.4.11f1',
        'ReleaseVersion': 'OB52',
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-GA': 'v1 1',
        'Authorization': f'Bearer {token}',
        'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 7.1.2; ASUS_Z01QD Build/QKQ1.190825.002)',
        'Host': 'clientbp.ggpolarbear.com',
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
# تغيير البايو مع إعادة المحاولة (باستخدام الدوال الجديدة)
# ═══════════════════════════════════════════════════════════════

async def async_change_bio_with_retry(uid, password, new_bio, region, semaphore, client):
    async with semaphore:
        for attempt in range(MAX_RETRIES):
            if attempt > 0:
                await asyncio.sleep(RETRY_DELAY)
            try:
                result = await asyncio.to_thread(change_bio_sync, uid, password, new_bio)
                if result.get('status') == 'نجاح':
                    return result
                if attempt < MAX_RETRIES - 1:
                    continue
                return result
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    continue
                return {'status': 'خطأ', 'error': str(e)[:30], 'uid': uid}
        return {'status': 'فشل', 'error': 'تجاوز الحد الأقصى للمحاولات', 'uid': uid}

async def async_change_bio_single(uid, password, new_bio, region):
    semaphore = asyncio.Semaphore(1)
    async with httpx.AsyncClient(verify=False) as client:
        return await async_change_bio_with_retry(uid, password, new_bio, region, semaphore, client)

# ═══════════════════════════════════════════════════════════════
# تشغيل بوت واحد (يتم استدعاؤه في عملية منفصلة)
# ═══════════════════════════════════════════════════════════════

def run_single_bot(folder, filename, bot_id, status_dict, stop_event, error_dict):
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
🤖 *مدير نظام البوتات - الشمقمق (الإصدار النهائي)*
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
• `/addbot` - لاستقبال ملف ZIP لإضافة بوت جديد
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
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ ليس لديك صلاحية!")
        return
    context.user_data['waiting_for_bot_zip'] = True
    await update.message.reply_text("📦 أرسل ملف ZIP الذي يحتوي على `main.py` (الملف الرئيسي للبوت).", parse_mode='Markdown')

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ ليس لديك صلاحية!")
        return
    if not context.user_data.get('waiting_for_bot_zip', False):
        return
    context.user_data['waiting_for_bot_zip'] = False
    document = update.message.document
    if not document or not document.file_name.endswith('.zip'):
        await update.message.reply_text("❗ يرجى إرسال ملف بصيغة ZIP فقط.")
        return
    await update.message.reply_text("⏳ جاري تحميل الملف...")
    file = await context.bot.get_file(document.file_id)
    temp_zip = os.path.join(CACHE_DIR, f"temp_{document.file_id}.zip")
    await file.download_to_drive(temp_zip)
    await update.message.reply_text("⏳ جاري فك الضغط وإعداد البوت...")
    folder, main_file = extract_and_setup_bot(temp_zip)
    os.remove(temp_zip)
    if not folder:
        await update.message.reply_text(f"❌ فشل في إعداد البوت: {main_file}")
        return
    bots = load_bots_config()
    new_bot = {
        "folder": folder,
        "main_file": main_file,
        "added_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    bots.append(new_bot)
    save_bots_config(bots)
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
    status_dict = context.bot_data.get('status_dict')
    stop_events = context.bot_data.get('stop_events')
    if bot_folder in bot_processes and bot_processes[bot_folder].is_alive():
        stop_bot_process(bot_folder, status_dict, stop_events)
    folder_path = bot_info['folder']
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
    bots = [b for b in bots if b['folder'] != bot_folder]
    save_bots_config(bots)
    await update.message.reply_text(f"✅ تم حذف البوت {bot_folder} ومجلده {folder_path}")

# ═══════════════════════════════════════════════════════════════
# أوامر Free Fire
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
    app.add_handler(CommandHandler("addbot", cmd_addbot_request))
    app.add_handler(CommandHandler("delbot", cmd_delbot))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
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
# خادم Flask لإبقاء الخدمة نشطة على Render
# ═══════════════════════════════════════════════════════════════

web_app = Flask(__name__)

@web_app.route('/')
def health_check():
    return "Bot Controller is running", 200

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host="0.0.0.0", port=port, debug=False)

def start_flask_thread():
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    print(f"🌐 خادم HTTP يعمل على المنفذ {os.environ.get('PORT', 10000)}")

# ═══════════════════════════════════════════════════════════════
# الشمقمق
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 بدء النظام - ZAKARIA (Dynamic Hosting)")
    print("=" * 50)
    ensure_cache_dir()
    ensure_log_dir()

    start_flask_thread()

    manager = Manager()
    status_dict = manager.dict()
    error_dict = manager.dict()
    stop_events = {}

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