import os
import logging
import threading
import time
import requests
import pymongo
import certifi
import pytz
from datetime import datetime, time as dt_time
from flask import Flask, request, jsonify
from urllib.parse import quote_plus

# ==============================================================================
# ⚠️ بياناتك الحساسة (تم وضعها كما طلبت ليعمل الكود فوراً)
# ==============================================================================

TELEGRAM_TOKEN = "8260168982:AAEy-YQDWa-yTqJKmsA_yeSuNtZb8qNeHAI"
ADMIN_ID = 7635779264

# إعداد رابط قاعدة البيانات مع تشفير كلمة المرور
RAW_PASSWORD = "mohamed862006&"
ESCAPED_PASSWORD = quote_plus(RAW_PASSWORD)
MONGO_URL = f"mongodb+srv://mohamedabdellah:{ESCAPED_PASSWORD}@cluster0.hvuqzjx.mongodb.net/?appName=Cluster0"

# روابط الاتصال
WEBHOOK_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://amina-3ryn.onrender.com") + "/webhook"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
TELEGRAM_PHOTO_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"

# ==============================================================================

# إعداد التطبيق
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
TIMEZONE = pytz.timezone("Africa/Algiers")
last_sent = {}

# --- الروابط والنصوص (تم دمجها) ---
MORNING_IMG_URL = "https://raw.githubusercontent.com/ha6119336-svg/amina/main/photo_2025-12-22_10-05-15.jpg"
EVENING_IMG_URL = "https://raw.githubusercontent.com/ha6119336-svg/amina/main/photo_2025-12-28_16-54-02.jpg"

GENERAL_DHIKR = """‏﴿ وَاذْكُر ربّكَ إِذَا نَسِيتَ ﴾ 🌿
‏- سُبحان الله
‏- الحمدلله
-‏ الله أكبر
‏- أستغفر الله
‏- لا إله إلا الله
‏- لاحول ولا قوة إلا بالله
‏- سُبحان الله وبحمده
‏- سُبحان الله العظيم
- اللَّهُمَّ صلِّ وسلِم على نبينا محمد
‏- لا إله إلا أنت سُبحانك إني كنت من الظالمين."""

SLEEP_DHIKR = """🌙 نام وأنت مغفور الذنب
قال رسول الله ﷺ:
"من قال حين يأوي إلى فراشه:
'لا إله إلا الله وحده لا شريك له، له الملك وله الحمد، وهو على كل شيء قدير، لا حول ولا قوة إلا بالله، سبحان الله والحمد لله ولا إله إلا الله والله أكبر'
غفر الله ذنوبه أو خطاياه وإن كانت مثل زبد البحر." 🤎🌗"""

START_RESPONSE = """🤖 بوت أذكار الصباح والمساء
يُرسل الأذكار والتذكيرات يومياً بتوقيت الجزائر:
🌅 08:30 | أذكار الصباح (صورة)
📿 11:00 | تذكير بالله (نص)
🌇 16:00 | أذكار المساء (صورة)
📿 17:00 | تذكير بالله (نص)
📿 21:00 | تذكير بالله (نص)
🌙 23:00 | أذكار النوم (نص)

👤 حساب المطوّر:
@Mik_emm
💡 صاحب الفكرة:
@mohamedelhocine
🤲 نرجو الدعاء له
بارك الله فيكم 🌸"""

# --- الاتصال بقاعدة البيانات ---
db_connected = False
chats_col = None

try:
    # مهلة 5 ثواني فقط للاتصال حتى لا يعلق البوت
    client = pymongo.MongoClient(MONGO_URL, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=5000)
    db = client["amina_db"]
    chats_col = db["chats"]
    # أمر بسيط للتأكد من الاتصال
    client.server_info()
    db_connected = True
    logging.info("✅ تم الاتصال بقاعدة البيانات بنجاح")
except Exception as e:
    logging.error(f"❌ فشل الاتصال بقاعدة البيانات (لكن البوت سيعمل): {e}")

# --- دوال مساعدة (Threads) ---

def send_message(chat_id, text):
    """إرسال رسالة نصية"""
    try:
        requests.post(TELEGRAM_API_URL, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}, timeout=5)
    except Exception as e:
        logging.error(f"Error Sending Text: {e}")

def send_photo(chat_id, photo_url, caption=None):
    """إرسال صورة"""
    try:
        requests.post(TELEGRAM_PHOTO_URL, json={"chat_id": chat_id, "photo": photo_url, "caption": caption, "parse_mode": "Markdown"}, timeout=10)
    except Exception as e:
        logging.error(f"Error Sending Photo: {e}")

def save_chat_background(chat_id, title, chat_type):
    """حفظ البيانات في الخلفية"""
    if not db_connected: return
    try:
        chats_col.update_one(
            {"chat_id": str(chat_id)},
            {"$set": {"chat_id": str(chat_id), "title": title, "type": chat_type, "active": True, "last_seen": datetime.now()}},
            upsert=True
        )
    except: pass

# --- نقل المجموعات القديمة (تشغيل مرة واحدة في الخلفية) ---
OLD_GROUPS = ["-1002225164483", "-1002576714713", "-1002704601167", "-1003191159502", "-1003177076554", "-1002820782492"]
def migrate_old_groups():
    if not db_connected: return
    time.sleep(10) # انتظار قليلاً حتى يستقر البوت
    for gid in OLD_GROUPS:
        try:
            chats_col.update_one({"chat_id": gid}, {"$set": {"active": True, "migrated": True}}, upsert=True)
        except: pass
threading.Thread(target=migrate_old_groups, daemon=True).start()

# --- المجدول الزمني (Scheduler) ---
def broadcast(content_type, content, caption=None):
    """نشر للجميع"""
    if not db_connected: return
    cursor = chats_col.find({"active": True})
    for doc in cursor:
        chat_id = doc["chat_id"]
        try:
            if content_type == "photo": send_photo(chat_id, content, caption)
            else: send_message(chat_id, content)
            time.sleep(0.05) 
        except: pass

def scheduler():
    while True:
        try:
            now = datetime.now(TIMEZONE)
            current_time = now.strftime("%H:%M")
            day_key = now.strftime("%Y-%m-%d")
            
            # جدول المواعيد (تم تعديله حسب طلبك)
            schedule = {
                "08:30": ("photo", MORNING_IMG_URL, "🌅 أذكار الصباح"),
                "11:27": ("text", GENERAL_DHIKR, None),
                "16:00": ("photo", EVENING_IMG_URL, "🌇 أذكار المساء"),
                "17:00": ("text", GENERAL_DHIKR, None),
                "21:00": ("text", GENERAL_DHIKR, None),
                "23:00": ("text", SLEEP_DHIKR, None)
            }

            if current_time in schedule:
                task_key = f"{day_key}_{current_time}"
                if task_key not in last_sent:
                    type_, content, caption = schedule[current_time]
                    broadcast(type_, content, caption)
                    last_sent[task_key] = True
                    # تنظيف الذاكرة
                    if len(last_sent) > 50: last_sent.clear(); last_sent[task_key] = True
            
            time.sleep(60)
        except Exception as e:
            logging.error(f"Scheduler Error: {e}")
            time.sleep(60)

threading.Thread(target=scheduler, daemon=True).start()

# --- الويب والـ Webhook ---

@app.route("/", methods=["GET"])
def home():
    return "Bot is Running Live!", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    if not data: return jsonify(ok=True)

    if "message" in data:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "").strip()
        
        # 1️⃣ الرد الفوري على Start (تم الإصلاح)
        if text.startswith("/start"):
            # نرسل الرد في خيط منفصل فوراً
            threading.Thread(target=send_message, args=(chat_id, START_RESPONSE)).start()
            # نحفظ البيانات في الخلفية
            threading.Thread(target=save_chat_background, args=(chat_id, msg["chat"].get("title", "User"), msg["chat"]["type"])).start()
            return jsonify(ok=True)

        # 2️⃣ الرد الفوري على ID (تم الإصلاح: يرسل رقمك فقط)
        elif text.startswith("/id"):
            threading.Thread(target=send_message, args=(chat_id, f"🆔 ID: `{chat_id}`")).start()
            return jsonify(ok=True)

        # 3️⃣ أوامر الأدمن
        elif text == "/admin" and msg.get("from", {}).get("id") == ADMIN_ID:
             count = chats_col.count_documents({"active": True}) if db_connected else 0
             threading.Thread(target=send_message, args=(chat_id, f"📊 عدد المشتركين: {count}")).start()
             return jsonify(ok=True)

        # حفظ الرسائل العادية
        title = msg["chat"].get("title", msg["chat"].get("first_name"))
        threading.Thread(target=save_chat_background, args=(chat_id, title, msg["chat"]["type"])).start()

    # معالجة الإضافة لمجموعة
    if "my_chat_member" in data:
        update = data["my_chat_member"]
        if update["new_chat_member"]["status"] in ["member", "administrator"]:
            chat = update["chat"]
            threading.Thread(target=save_chat_background, args=(chat["id"], chat.get("title"), "group")).start()

    return jsonify(ok=True)

# Ping للحفاظ على البوت
def keep_alive():
    while True:
        try: requests.get(f"{WEBHOOK_URL.replace('/webhook', '')}/")
        except: pass
        time.sleep(800)
threading.Thread(target=keep_alive, daemon=True).start()

if __name__ == "__main__":
    # تفعيل الويب هوك تلقائياً
    try:
        requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook?url={WEBHOOK_URL}")
        logging.info("Webhook Set Successfully")
    except: pass
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
