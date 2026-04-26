#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#🇲🇦🇲🇦🇲🇦
#عدل اي شيء لا مشكلة ابدا #@ZikoB0SS _AYOUB _ZAKARIA _FPI_SX_TEM

import os
import sys
import json
import time
import subprocess
import shutil
import zipfile
import threading
import re
import traceback
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    filters, ContextTypes
)
from telegram.constants import ParseMode
from telegram.error import NetworkError, TimedOut, BadRequest

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

#عدل اي شيء لا مشكلة ابدل #@ZikoB0SS _AYOUB _ZAKARIA _FPI_SX_TEM
TELEGRAM_BOT_TOKEN = "8301372114:AAGx78W1ThiF033soCLuXISkAd2UttgEC8E"
ADMIN_IDS = [6848455321, 7375963526]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, "cache")
LOG_DIR = os.path.join(BASE_DIR, "logs")
BOTS_DIR = os.path.join(BASE_DIR, "bots")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

for folder in [CACHE_DIR, LOG_DIR, BOTS_DIR, UPLOAD_DIR]:
    os.makedirs(folder, exist_ok=True)

BOTS_CONFIG_FILE = os.path.join(CACHE_DIR, "bots_config.json")
running_bots = {}

# ------------------ إدارة السجلات ------------------
def truncate_log_file(file_path, max_lines=100):
    """قص ملف السجل للاحتفاظ بآخر max_lines سطر فقط."""
    if not os.path.exists(file_path):
        return
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        if len(lines) > max_lines:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines[-max_lines:])
    except Exception as e:
        print(f"خطأ في قص ملف السجل {file_path}: {e}")

# ------------------ دوال البوتات ------------------
def load_bots():
    if not os.path.exists(BOTS_CONFIG_FILE):
        return []
    try:
        with open(BOTS_CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_bots(bots):
    with open(BOTS_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(bots, f, indent=4, ensure_ascii=False)

def get_unique_folder(name):
    base = "".join(c for c in name if c.isalnum() or c in ('-', '_')).strip()
    if not base:
        base = "bot"
    folder = base
    counter = 1
    while os.path.exists(os.path.join(BOTS_DIR, folder)):
        folder = f"{base}_{counter}"
        counter += 1
    return folder

def install_requirements(bot_folder):
    req_file = os.path.join(bot_folder, 'requirements.txt')
    if not os.path.exists(req_file):
        return True, "لا يوجد requirements.txt"
    lib_dir = os.path.join(bot_folder, 'lib')
    os.makedirs(lib_dir, exist_ok=True)
    try:
        cmd = [sys.executable, '-m', 'pip', 'install', '-r', req_file, '--target', lib_dir, '--upgrade', '--no-cache-dir']
        subprocess.run(cmd, capture_output=True, timeout=180)
        with open(os.path.join(bot_folder, 'sitecustomize.py'), 'w') as f:
            f.write("""import sys, os
lib_path = os.path.join(os.path.dirname(__file__), 'lib')
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)
""")
        return True, "تم تثبيت المكتبات"
    except Exception as e:
        return False, str(e)

def extract_and_setup_bot(zip_path, bot_name):
    folder_name = get_unique_folder(bot_name)
    target_dir = os.path.join(BOTS_DIR, folder_name)
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(target_dir)
        main_file = None
        for root, dirs, files in os.walk(target_dir):
            for f in files:
                if f in ('main.py', 'app.py', 'bot.py'):
                    main_file = os.path.relpath(os.path.join(root, f), target_dir)
                    break
            if main_file:
                break
        if not main_file:
            shutil.rmtree(target_dir)
            return None, None, "لم يتم العثور على main.py أو app.py أو bot.py"
        install_requirements(target_dir)
        return folder_name, main_file, "تم إعداد البوت بنجاح"
    except Exception as e:
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
        return None, None, str(e)

def edit_token_in_file(file_path, new_token):
    if not os.path.exists(file_path):
        return False
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    patterns = [
        r'(TELEGRAM_BOT_TOKEN\s*=\s*["\'])([^"\']*)(["\'])',
        r'(TOKEN\s*=\s*["\'])([^"\']*)(["\'])',
        r'(BOT_TOKEN\s*=\s*["\'])([^"\']*)(["\'])',
        r'(API_TOKEN\s*=\s*["\'])([^"\']*)(["\'])'
    ]
    replaced = False
    for pat in patterns:
        new_content, count = re.subn(pat, r'\g<1>' + new_token + r'\g<3>', content)
        if count > 0:
            content = new_content
            replaced = True
            break
    if not replaced:
        return False
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return True

def edit_bot_token(bot_id, new_token):
    bots = load_bots()
    bot = next((b for b in bots if b['id'] == bot_id), None)
    if not bot:
        return False, "البوت غير موجود"
    folder_path = os.path.join(BOTS_DIR, bot['folder'])
    for filename in ['main.py', 'app.py', 'bot.py']:
        file_path = os.path.join(folder_path, filename)
        if os.path.exists(file_path) and edit_token_in_file(file_path, new_token):
            return True, f"✅ تم تعديل التوكن في {filename}"
    return False, "❌ لم يتم العثور على ملف يحتوي على التوكن"

def kill_process_tree(pid):
    if not HAS_PSUTIL:
        return False
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        for child in children:
            child.terminate()
        _, alive = psutil.wait_procs(children, timeout=3)
        for p in alive:
            p.kill()
        parent.terminate()
        parent.wait(3)
        return True
    except:
        return False

def run_bot(bot_id, folder, main_file):
    log_file = os.path.join(LOG_DIR, f"{bot_id}.log")
    truncate_log_file(log_file)
    env = os.environ.copy()
    lib_dir = os.path.join(BOTS_DIR, folder, 'lib')
    if os.path.exists(lib_dir):
        env['PYTHONPATH'] = lib_dir + os.pathsep + env.get('PYTHONPATH', '')
    with open(log_file, 'a', encoding='utf-8') as log:
        log.write(f"\n{'='*50}\n[{datetime.now()}] بدء تشغيل البوت {bot_id}\n")
        process = subprocess.Popen(
            [sys.executable, main_file],
            cwd=os.path.join(BOTS_DIR, folder),
            stdout=log,
            stderr=subprocess.STDOUT,
            env=env
        )
        running_bots[bot_id] = process
        process.wait()
        log.write(f"[{datetime.now()}] توقف البوت {bot_id}\n")
    if bot_id in running_bots:
        del running_bots[bot_id]
    truncate_log_file(log_file)

def start_bot(bot_id):
    bots = load_bots()
    bot = next((b for b in bots if b['id'] == bot_id), None)
    if not bot:
        return False, "❌ البوت غير موجود"
    if bot_id in running_bots and running_bots[bot_id].poll() is None:
        return False, "⚠️ البوت يعمل بالفعل"
    threading.Thread(target=run_bot, args=(bot_id, bot['folder'], bot['main_file']), daemon=True).start()
    return True, "✅ تم تشغيل البوت"

def stop_bot(bot_id):
    if bot_id not in running_bots:
        return False, "⚠️ البوت ليس قيد التشغيل"
    proc = running_bots[bot_id]
    if proc.poll() is None:
        if HAS_PSUTIL:
            kill_process_tree(proc.pid)
        else:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
    if bot_id in running_bots:
        del running_bots[bot_id]
    time.sleep(0.5)
    return True, "✅ تم إيقاف البوت"

def restart_bot(bot_id):
    stop_bot(bot_id)
    time.sleep(2)
    return start_bot(bot_id)

def delete_bot(bot_id):
    bots = load_bots()
    bot = next((b for b in bots if b['id'] == bot_id), None)
    if not bot:
        return False, "❌ البوت غير موجود"
    if bot_id in running_bots:
        try:
            stop_bot(bot_id)
        except Exception as e:
            print(f"خطأ أثناء إيقاف البوت {bot_id}: {e}")
    folder_path = os.path.join(BOTS_DIR, bot['folder'])
    if not os.path.exists(folder_path):
        bots = [b for b in bots if b['id'] != bot_id]
        save_bots(bots)
        return True, "✅ تم حذف البوت (المجلد غير موجود)"
    try:
        shutil.rmtree(folder_path)
    except Exception as e:
        return False, f"❌ فشل حذف المجلد: {str(e)}"
    bots = [b for b in bots if b['id'] != bot_id]
    save_bots(bots)
    log_file = os.path.join(LOG_DIR, f"{bot_id}.log")
    if os.path.exists(log_file):
        try:
            os.remove(log_file)
        except:
            pass
    return True, "✅ تم حذف البوت"

def delete_all_bots():
    bots = load_bots()
    count = len(bots)
    for bot in bots:
        try:
            if bot['id'] in running_bots:
                stop_bot(bot['id'])
            folder_path = os.path.join(BOTS_DIR, bot['folder'])
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path)
            log_file = os.path.join(LOG_DIR, f"{bot['id']}.log")
            if os.path.exists(log_file):
                os.remove(log_file)
        except Exception as e:
            print(f"خطأ أثناء حذف البوت {bot['id']}: {e}")
    save_bots([])
    return True, f"✅ تم حذف {count} بوت"

def stop_all_bots():
    stopped = 0
    for bot_id in list(running_bots.keys()):
        try:
            stop_bot(bot_id)
            stopped += 1
        except:
            pass
    return stopped

#عدل اي شيء لا مشكلة ابدل #@ZikoB0SS _AYOUB _ZAKARIA _FPI_SX_TEM
async def safe_send_message(chat_id, text, reply_markup=None, parse_mode=None):
    try:
        return await chat_id.send_message(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except BadRequest as e:
        if "Can't parse entities" in str(e) and parse_mode is not None:
            return await chat_id.send_message(text, reply_markup=reply_markup, parse_mode=None)
        raise

async def safe_edit_message(query, text, reply_markup=None, parse_mode=None):
    try:
        return await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except BadRequest as e:
        if "Can't parse entities" in str(e) and parse_mode is not None:
            return await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=None)
        raise

def is_admin(user_id):
    return user_id in ADMIN_IDS

async def close_message(query):
    """حذف رسالة القائمة عند الضغط على زر الإغلاق"""
    try:
        await query.message.delete()
    except:
        await query.answer("لا يمكن حذف الرسالة.")

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ هذا البوت للمشرفين فقط.")
        return
    await show_main_menu(update.message)

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ هذا البوت للمشرفين فقط.")
        return
    help_text = (
        "🌟 **مرحباً بك في مدير البوتات**\n\n"
        "📌 **الأوامر المتاحة:**\n"
        "/start - عرض القائمة الرئيسية\n"
        "/help - عرض هذه الرسالة\n\n"
        "📌 **كيفية الاستخدام:**\n"
        "1. استخدم /start لفتح القائمة.\n"
        "2. اختر 'إدارة البوتات' لعرض البوتات المضافة.\n"
        "3. لإضافة بوت جديد: اضغط '➕ إضافة بوت'، ثم أدخل اسماً وأرسل ملف ZIP.\n"
        "4. للتحكم في بوت: اضغط على اسمه، ثم استخدم أزرار التشغيل والإيقاف والحذف.\n"
        "5. يمكنك تعديل التوكن مباشرة من صفحة البوت.\n\n"
        "⚠️ **🇲🇦ملاحظات🇲🇦:**\n"
        "- ملف ZIP يجب أن يحتوي على main.py أو app.py أو bot.py.\n"
        "- المكتبات المطلوبة توضع في requirements.txt.\n"
        "- يمكن تثبيت psutil لتحسين إدارة العمليات: `pip install psutil`"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def show_main_menu(message):
    keyboard = [
        [InlineKeyboardButton("📊 لوحة التحكم", callback_data="dashboard")],
        [InlineKeyboardButton("🤖 إدارة البوتات", callback_data="manage_bots")],
        [InlineKeyboardButton("🛑 إيقاف المدير", callback_data="confirm_stop_manager")],
        [InlineKeyboardButton("❌ إغلاق", callback_data="close_message")],
    ]
    await message.reply_text(
        "🌟 **مرحباً بك في FPI SX MANAGER**\nاختر إحدى الخيارات:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def show_main_menu_edit(query):
    keyboard = [
        [InlineKeyboardButton("📊 لوحة التحكم", callback_data="dashboard")],
        [InlineKeyboardButton("🤖 إدارة البوتات", callback_data="manage_bots")],
        [InlineKeyboardButton("🛑 إيقاف المدير", callback_data="confirm_stop_manager")],
        [InlineKeyboardButton("❌ إغلاق", callback_data="close_message")],
    ]
    try:
        await safe_edit_message(query,
            "🌟 **مرحباً بك في FPI SX MANAGER**\nاختر إحدى الخيارات:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    except BadRequest as e:
        if "Message is not modified" in str(e):
            pass
        else:
            raise

async def show_dashboard(query):
    bots = load_bots()
    running = sum(1 for b in bots if b['id'] in running_bots and running_bots[b['id']].poll() is None)
    text = (
        f"📊 **لوحة التحكم**\n\n"
        f"📦 إجمالي البوتات: `{len(bots)}`\n"
        f"🟢 يعمل: `{running}`\n"
        f"🔴 متوقف: `{len(bots)-running}`"
    )
    keyboard = [
        [InlineKeyboardButton("⏹️ إيقاف جميع البوتات", callback_data="confirm_stop_all")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"),
         InlineKeyboardButton("❌ إغلاق", callback_data="close_message")],
    ]
    await safe_edit_message(query, text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def show_bots_list(query):
    bots = load_bots()
    if not bots:
        keyboard = [
            [InlineKeyboardButton("➕ إضافة بوت", callback_data="add_bot")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"),
             InlineKeyboardButton("❌ إغلاق", callback_data="close_message")]
        ]
        await safe_edit_message(query, "📭 لا توجد بوتات.", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    keyboard = []
    for bot in bots:
        status = "🟢" if bot['id'] in running_bots and running_bots[bot['id']].poll() is None else "🔴"
        keyboard.append([InlineKeyboardButton(f"{status} {bot['name']}", callback_data=f"bot_info_{bot['id']}")])
    keyboard.append([InlineKeyboardButton("➕ إضافة بوت", callback_data="add_bot")])
    keyboard.append([InlineKeyboardButton("🗑️ حذف الكل", callback_data="confirm_delete_all")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"),
                     InlineKeyboardButton("❌ إغلاق", callback_data="close_message")])
    await safe_edit_message(query, "📋 **قائمة البوتات:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def show_bot_info(query, bot_id):
    bots = load_bots()
    bot = next((b for b in bots if b['id'] == bot_id), None)
    if not bot:
        await query.answer("❌ البوت غير موجود")
        await show_bots_list(query)
        return
    status = "🟢 يعمل" if bot['id'] in running_bots and running_bots[bot['id']].poll() is None else "🔴 متوقف"
    text = (
        f"🤖 <b>{bot['name']}</b>\n"
        f"🆔 <code>{bot['id']}</code>\n"
        f"📁 <code>{bot['folder']}</code>\n"
        f"📄 <code>{bot['main_file']}</code>\n"
        f"📊 الحالة: {status}"
    )
    keyboard = [
        [InlineKeyboardButton("▶️ تشغيل", callback_data=f"bot_start_{bot['id']}"),
         InlineKeyboardButton("⏹️ إيقاف", callback_data=f"bot_stop_{bot['id']}"),
         InlineKeyboardButton("🔄 إعادة تشغيل", callback_data=f"bot_restart_{bot['id']}")],
        [InlineKeyboardButton("✏️ تعديل التوكن", callback_data=f"bot_edit_token_{bot['id']}"),
         InlineKeyboardButton("🔄 تحديث الحالة", callback_data=f"bot_refresh_{bot['id']}")],
        [InlineKeyboardButton("📜 عرض السجل", callback_data=f"bot_log_{bot['id']}"),
         InlineKeyboardButton("🗑️ حذف", callback_data=f"confirm_delete_{bot['id']}")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="manage_bots"),
         InlineKeyboardButton("❌ إغلاق", callback_data="close_message")]
    ]
    try:
        await safe_edit_message(query, text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    except BadRequest as e:
        if "Message is not modified" in str(e):
            pass
        else:
            raise

async def show_log(query, bot_id):
    log_file = os.path.join(LOG_DIR, f"{bot_id}.log")
    truncate_log_file(log_file)
    if not os.path.exists(log_file):
        await safe_edit_message(query, "📭 لا يوجد سجل لهذا البوت.")
        return
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()[-100:]
        log_text = "".join(lines)
    if len(log_text) > 4000:
        log_text = log_text[-4000:]
    keyboard = [
        [InlineKeyboardButton("🔙 رجوع", callback_data=f"bot_info_{bot_id}")],
        [InlineKeyboardButton("❌ إغلاق", callback_data="close_message")]
    ]
    await safe_edit_message(query, f"📄 **سجل البوت** `{bot_id}`:\n```\n{log_text}\n```", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await query.edit_message_text("⛔ غير مصرح")
        return

    if data == "confirm_delete_all":
        keyboard = [
            [InlineKeyboardButton("✅ نعم، احذف الكل", callback_data="delete_all_bots")],
            [InlineKeyboardButton("❌ لا، إلغاء", callback_data="manage_bots")]
        ]
        await safe_edit_message(query, "⚠️ **تحذير:** هل أنت متأكد من حذف جميع البوتات نهائياً؟", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    elif data.startswith("confirm_delete_"):
        bot_id = data[15:]
        context.user_data['delete_bot_id'] = bot_id
        keyboard = [
            [InlineKeyboardButton("✅ نعم، احذف", callback_data=f"execute_delete_{bot_id}")],
            [InlineKeyboardButton("❌ لا، إلغاء", callback_data=f"bot_info_{bot_id}")]
        ]
        await safe_edit_message(query, "⚠️ **تحذير:** هل أنت متأكد من حذف هذا البوت؟", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    elif data == "confirm_stop_manager":
        keyboard = [
            [InlineKeyboardButton("✅ نعم، أوقف المدير", callback_data="stop_manager")],
            [InlineKeyboardButton("❌ لا، إلغاء", callback_data="back_to_main")]
        ]
        await safe_edit_message(query, "⚠️ **تحذير:** إيقاف المدير سيغلق هذا البوت بالكامل. هل أنت متأكد؟", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "confirm_stop_all":
        keyboard = [
            [InlineKeyboardButton("✅ نعم، أوقف الجميع", callback_data="stop_all_bots")],
            [InlineKeyboardButton("❌ لا، إلغاء", callback_data="dashboard")]
        ]
        await safe_edit_message(query, "⚠️ **تحذير:** هل تريد إيقاف جميع البوتات المشغلة؟", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await query.edit_message_text("⛔ غير مصرح")
        return
    try:
        if data == "close_message":
            await close_message(query)
            return
        elif data == "dashboard":
            await show_dashboard(query)
        elif data == "manage_bots":
            await show_bots_list(query)
        elif data == "back_to_main":
            await show_main_menu_edit(query)
        elif data == "delete_all_bots":
            success, msg = delete_all_bots()
            await query.answer(msg)
            if success:
                await show_bots_list(query)
        elif data == "stop_all_bots":
            count = stop_all_bots()
            await query.answer(f"✅ تم إيقاف {count} بوت")
            await show_dashboard(query)
        elif data == "stop_manager":
            await query.edit_message_text("🛑 جاري إيقاف بوت المدير...")
            await context.application.stop()
            sys.exit(0)
        elif data.startswith("bot_info_"):
            bot_id = data[9:]
            await show_bot_info(query, bot_id)
        elif data.startswith("bot_log_"):
            bot_id = data[8:]
            await show_log(query, bot_id)
        elif data.startswith("bot_refresh_"):
            bot_id = data[12:]
            await show_bot_info(query, bot_id)
        elif data.startswith("bot_start_"):
            bot_id = data[10:]
            success, msg = start_bot(bot_id)
            await query.answer(msg)
            if success:
                await show_bot_info(query, bot_id)
        elif data.startswith("bot_stop_"):
            bot_id = data[9:]
            success, msg = stop_bot(bot_id)
            await query.answer(msg)
            await show_bot_info(query, bot_id)
        elif data.startswith("bot_restart_"):
            bot_id = data[12:]
            success, msg = restart_bot(bot_id)
            await query.answer(msg)
            await show_bot_info(query, bot_id)
        elif data.startswith("execute_delete_"):
            bot_id = data[15:]
            success, msg = delete_bot(bot_id)
            await query.answer(msg)
            if success:
                await show_bots_list(query)
            else:
                await safe_edit_message(query, f"⚠️ {msg}\n\nلم يتم حذف البوت.", reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 رجوع", callback_data=f"bot_info_{bot_id}")]
                ]))
        elif data.startswith("bot_edit_token_"):
            bot_id = data[16:]
            context.user_data['edit_token_bot'] = bot_id
            await query.edit_message_text("🔑 أرسل التوكن الجديد للبوت:")
        elif data == "add_bot":
            context.user_data['waiting_for_bot_name'] = True
            await query.edit_message_text("✏️ أدخل اسم البوت:")
        else:
            await query.answer("❓ زر غير معروف")
    except Exception as e:
        print(f"خطأ في button_handler: {e}")
        traceback.print_exc()
        try:
            await query.edit_message_text(f"⚠️ حدث خطأ: {str(e)}")
        except:
            pass

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    if not update.message or not update.message.text:
        return
    text = update.message.text.strip()
    if context.user_data.get('waiting_for_bot_name'):
        bot_name = text
        context.user_data['bot_name'] = bot_name
        context.user_data['waiting_for_bot_name'] = False
        context.user_data['waiting_for_zip'] = True
        await update.message.reply_text(f"📛 اسم البوت: `{bot_name}`\n📦 الآن أرسل ملف ZIP للبوت.", parse_mode=ParseMode.MARKDOWN)
        return
    if context.user_data.get('edit_token_bot'):
        bot_id = context.user_data.pop('edit_token_bot')
        new_token = text
        success, msg = edit_bot_token(bot_id, new_token)
        await update.message.reply_text(msg)
        await show_bot_info_for_message(update, bot_id)
        return

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    if not context.user_data.get('waiting_for_zip'):
        return
    document = update.message.document
    if not document or not document.file_name.endswith('.zip'):
        await update.message.reply_text("❗ أرسل ملف ZIP صالح.")
        return
    bot_name = context.user_data.get('bot_name')
    if not bot_name:
        await update.message.reply_text("❗ لم يتم إرسال اسم البوت. أعد المحاولة.")
        context.user_data.pop('waiting_for_zip')
        return
    await update.message.reply_text("⏳ جاري تحميل الملف...")
    file = await context.bot.get_file(document.file_id)
    temp_zip = os.path.join(UPLOAD_DIR, f"temp_{int(time.time())}.zip")
    await file.download_to_drive(temp_zip)
    await update.message.reply_text("⚙️ جاري فك الضغط وإعداد البوت...")
    folder, main_file, msg = extract_and_setup_bot(temp_zip, bot_name)
    os.remove(temp_zip)
    if not folder:
        await update.message.reply_text(f"❌ فشل: {msg}")
        context.user_data.pop('waiting_for_zip')
        context.user_data.pop('bot_name', None)
        return
    bot_id = f"bot_{int(time.time())}_{folder}"
    bots = load_bots()
    bots.append({
        'id': bot_id,
        'name': bot_name,
        'folder': folder,
        'main_file': main_file,
        'added_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    save_bots(bots)
    await update.message.reply_text(f"✅ تمت إضافة البوت `{bot_name}` بنجاح.\nيمكنك الآن تشغيله من القائمة.", parse_mode=ParseMode.MARKDOWN)
    context.user_data.pop('waiting_for_zip')
    context.user_data.pop('bot_name', None)

async def show_bot_info_for_message(update, bot_id):
    bots = load_bots()
    bot = next((b for b in bots if b['id'] == bot_id), None)
    if not bot:
        await update.message.reply_text("❌ البوت غير موجود")
        return
    status = "🟢 يعمل" if bot['id'] in running_bots and running_bots[bot['id']].poll() is None else "🔴 متوقف"
    text = (
        f"🤖 **{bot['name']}**\n"
        f"🆔 `{bot['id']}`\n"
        f"📁 `{bot['folder']}`\n"
        f"📄 `{bot['main_file']}`\n"
        f"📊 الحالة: {status}"
    )
    keyboard = [
        [InlineKeyboardButton("▶️ تشغيل", callback_data=f"bot_start_{bot['id']}"),
         InlineKeyboardButton("⏹️ إيقاف", callback_data=f"bot_stop_{bot['id']}"),
         InlineKeyboardButton("🔄 إعادة تشغيل", callback_data=f"bot_restart_{bot['id']}")],
        [InlineKeyboardButton("✏️ تعديل التوكن", callback_data=f"bot_edit_token_{bot['id']}"),
         InlineKeyboardButton("🔄 تحديث الحالة", callback_data=f"bot_refresh_{bot['id']}")],
        [InlineKeyboardButton("📜 عرض السجل", callback_data=f"bot_log_{bot['id']}"),
         InlineKeyboardButton("🗑️ حذف", callback_data=f"confirm_delete_{bot['id']}")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="manage_bots"),
         InlineKeyboardButton("❌ إغلاق", callback_data="close_message")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if isinstance(context.error, (NetworkError, TimedOut)):
        print(f"⚠️ خطأ شبكة: {context.error}")
    else:
        print(f"❌ خطأ: {context.error}")
        traceback.print_exc()

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_error_handler(error_handler)
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(?!confirm_)"))
    app.add_handler(CallbackQueryHandler(handle_confirmation, pattern="^confirm_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    print("🚀 تم تشغيل بوت FPI SX MANAGER بنجاح!")
    print("👥 المشرفون:", ADMIN_IDS)
    print("ℹ️  ملاحظة: إذا كنت تريد قتل العمليات بشكل أفضل، قم بتثبيت psutil: pip install psutil")
    app.run_polling()

if __name__ == "__main__":
    main()
