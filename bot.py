import os
import logging
import threading
import time
import requests
import pymongo
import pytz
from datetime import datetime, time as dt_time
from flask import Flask, request, jsonify
from urllib.parse import quote_plus

# ==============================================================================
# ⚙️ الإعدادات (كل شيء جاهز)
# ==============================================================================

TELEGRAM_TOKEN = "8260168982:AAEy-YQDWa-yTqJKmsA_yeSuNtZb8qNeHAI"
ADMIN_ID = 7635779264

# قائمة المجموعات القديمة (احتياطية لضمان عمل البوت حتى لو تعطلت القاعدة)
BACKUP_GROUPS = ["-1002225164483", "-1002576714713", "-1002704601167", "-1003191159502", "-1003177076554"]

# إعدادات قاعدة البيانات
RAW_PASSWORD = "mohamed862006&"
ESCAPED_PASSWORD = quote_plus(RAW_PASSWORD)
MONGO_URL = f"mongodb+srv://mohamedabdellah:{ESCAPED_PASSWORD}@cluster0.hvuqzjx.mongodb.net/?appName=Cluster0"

# روابط الاتصال
WEBHOOK_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://amina-3ryn.onrender.com") + "/webhook"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
TELEGRAM_PHOTO_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
TIMEZONE = pytz.timezone("Africa/Algiers")
last_sent = {}

# ==============================================================================
# 🗄️ الاتصال بقاعدة البيانات (مع وضع الأمان لعدم تعطيل البوت)
# ==============================================================================
db_connected = False
chats_col = None

def connect_db():
    global db_connected, chats_col
    try:
        # إضافة tlsAllowInvalidCertificates=True لحل مشكلة Render
        client = pymongo.MongoClient(MONGO_URL, tls=True, tlsAllowInvalidCertificates=True, serverSelectionTimeoutMS=5000)
        db = client["amina_db"]
        chats_col = db["chats"]
        client.admin.command('ping') # فحص سريع
        db_connected = True
        logging.info("✅ Database Connected Successfully!")
    except Exception as e:
        logging.error(f"⚠️ Database Connection Failed (Bot will run in backup mode): {e}")

# نشغل الاتصال في خيط منفصل حتى لا يؤخر تشغيل البوت
threading.Thread(target=connect_db).start()

# ==============================================================================
# 📝 البيانات والمواعيد
# ==============================================================================

MORNING_IMG_URL = "https://raw.githubusercontent.com/ha6119336-svg/amina/main/photo_2025-12-22_10-05-15.jpg"
EVENING_IMG_URL = "https://raw.githubusercontent.com/ha6119336-svg/amina/main/photo_2025-12-28_16-54-02.jpg"

GENERAL_DHIKR = """‏﴿ وَاذْكُر ربّكَ إِذَا نَسِيتَ ﴾ 🌿
‏- سُبحان الله
‏- الحمدلله
-‏ الله أكبر
‏- أستغفر الله
‏- لا إله إلا الله
‏- لاحول ولا قوة إلا بالله"""

SLEEP_DHIKR = """🌙 *أذكار النوم*
"من قال حين يأوي إلى فراشه:
'لا إله إلا الله وحده لا شريك له...'
غفر الله ذنوبه." 🤎"""

START_RESPONSE = """🤖 *أهلاً بك في بوت الأذكار*
يُرسل الأذكار والتذكيرات يومياً بتوقيت الجزائر 🇩🇿

✅ البوت يعمل والحمد لله.
"""

# ==============================================================================
# 🚀 دوال الإرسال (سريعة جداً باستخدام requests)
# ==============================================================================

def send_message(chat_id, text):
    try:
        requests.post(TELEGRAM_API_URL, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}, timeout=5)
    except: pass

def send_photo(chat_id, photo_url, caption=None):
    try:
        requests.post(TELEGRAM_PHOTO_URL, json={"chat_id": chat_id, "photo": photo_url, "caption": caption, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def get_all_chats():
    """جلب المجموعات من الداتا بيز، وإذا فشل نستخدم القائمة الاحتياطية"""
    if db_connected and chats_col:
        try:
            db_chats = [doc["chat_id"] for doc in chats_col.find({"active": True})]
            # ندمج المجموعات القديمة مع الجديدة لضمان عدم ضياع أي أحد
            return list(set(db_chats + BACKUP_GROUPS))
        except:
            return BACKUP_GROUPS
    return BACKUP_GROUPS

def save_chat_background(chat_id, title, chat_type):
    """حفظ المجموعة دون انتظار"""
    if not db_connected: return
    try:
        chats_col.update_one(
            {"chat_id": str(chat_id)},
            {"$set": {"chat_id": str(chat_id), "title": title, "type": chat_type, "active": True, "last_seen": datetime.now()}},
            upsert=True
        )
    except: pass

# ==============================================================================
# ⏰ المجدول الزمني (Scheduler)
# ==============================================================================

def broadcast(content_type, content, caption=None):
    targets = get_all_chats()
    for chat_id in targets:
        # إرسال لكل مجموعة في خيط منفصل للسرعة
        if content_type == "photo":
            threading.Thread(target=send_photo, args=(chat_id, content, caption)).start()
        else:
            threading.Thread(target=send_message, args=(chat_id, content)).start()
        time.sleep(0.1) 

def scheduler():
    while True:
        try:
            now = datetime.now(TIMEZONE)
            current_time = now.strftime("%H:%M")
            day_key = now.strftime("%Y-%m-%d")
            
            schedule = {
                "08:30": ("photo", MORNING_IMG_URL, "🌅 أذكار الصباح"),
                "11:41": ("text", GENERAL_DHIKR, None),
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

# ==============================================================================
# 🌐 خادم الويب (Flask)
# ==============================================================================

@app.route("/", methods=["GET"])
def home():
    return "Bot is Running Fast!", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    if not data: return jsonify(ok=True)

    if "message" in data:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "").strip()
        
        # ✅ الرد السريع جداً
        if text.startswith("/start"):
            threading.Thread(target=send_message, args=(chat_id, START_RESPONSE)).start()
            threading.Thread(target=save_chat_background, args=(chat_id, msg["chat"].get("title", "User"), msg["chat"]["type"])).start()
            return jsonify(ok=True)

        elif text.startswith("/id"):
            threading.Thread(target=send_message, args=(chat_id, f"🆔: `{chat_id}`")).start()
            return jsonify(ok=True)

        # حفظ أي رسالة
        threading.Thread(target=save_chat_background, args=(chat_id, msg["chat"].get("title"), msg["chat"]["type"])).start()

    if "my_chat_member" in data:
        update = data["my_chat_member"]
        if update["new_chat_member"]["status"] in ["member", "administrator"]:
            chat = update["chat"]
            threading.Thread(target=save_chat_background, args=(chat["id"], chat.get("title"), "group")).start()

    return jsonify(ok=True)

# Ping Keep Alive
def keep_alive():
    while True:
        try: requests.get(f"{WEBHOOK_URL.replace('/webhook', '')}/")
        except: pass
        time.sleep(800)
threading.Thread(target=keep_alive, daemon=True).start()

if __name__ == "__main__":
    # Webhook Setup
    try:
        requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook?url={WEBHOOK_URL}")
    except: pass
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
