import os, logging, asyncio, threading, time, requests
from datetime import datetime, time as dt_time
import pytz
from flask import Flask, request, jsonify
from telegram import Bot, error
import pymongo
import certifi
from urllib.parse import quote_plus

# --- الإعدادات ---
TELEGRAM_TOKEN = "8260168982:AAEy-YQDWa-yTqJKmsA_yeSuNtZb8qNeHAI"
ADMIN_ID = 7635779264
WEBHOOK_URL = "https://amina-3ryn.onrender.com/webhook"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

# --- إعدادات قاعدة البيانات ---
RAW_PASSWORD = "mohamed862006&"
ESCAPED_PASSWORD = quote_plus(RAW_PASSWORD)
MONGO_URL = f"mongodb+srv://mohamedabdellah:{ESCAPED_PASSWORD}@cluster0.hvuqzjx.mongodb.net/?appName=Cluster0"

# الاتصال بقاعدة البيانات (تم إصلاح مشكلة SSL هنا)
try:
    client = pymongo.MongoClient(MONGO_URL, tlsCAFile=certifi.where())
    db = client["amina_db"]
    chats_col = db["chats"]
    logging.info("✅ تم الاتصال بقاعدة البيانات بنجاح")
except Exception as e:
    logging.error(f"❌ خطأ في الاتصال بقاعدة البيانات: {e}")

# --- المتغيرات العامة ---
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
bot = Bot(token=TELEGRAM_TOKEN)
last_sent = {}
TIMEZONE = pytz.timezone("Africa/Algiers")
event_loop = asyncio.new_event_loop()

# تشغيل Loop في الخلفية
def run_loop(loop): asyncio.set_event_loop(loop); loop.run_forever()
threading.Thread(target=run_loop, args=(event_loop,), daemon=True).start()

# --- نقل المجموعات القديمة ---
OLD_GROUPS_TO_MIGRATE = [
    "-1002225164483", "-1002576714713", "-1002704601167", 
    "-1003191159502", "-1003177076554", "-1002820782492"
]
def migrate_old_groups():
    for gid in OLD_GROUPS_TO_MIGRATE:
        try:
            chats_col.update_one(
                {"chat_id": gid},
                {"$set": {"chat_id": gid, "type": "group", "active": True, "migrated": True}},
                upsert=True
            )
        except: pass
threading.Thread(target=migrate_old_groups, daemon=True).start()

# --- روابط الصور ---
MORNING_IMG_URL = "https://raw.githubusercontent.com/ha6119336-svg/amina/main/photo_2025-12-22_10-05-15.jpg"
EVENING_IMG_URL = "https://raw.githubusercontent.com/ha6119336-svg/amina/main/photo_2025-12-28_16-54-02.jpg"

# --- المواعيد والنصوص ---
MORNING_TIME = dt_time(8, 30)
EVENING_TIME = dt_time(16, 0)
NIGHT_TIME = dt_time(23, 0)
REMINDER_TIME_1 = dt_time(11, 10)
REMINDER_TIME_2 = dt_time(17, 0)
REMINDER_TIME_3 = dt_time(21, 0)

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

# --- دوال مساعدة ---
def get_bot():
    global bot
    if not bot: bot = Bot(token=TELEGRAM_TOKEN)
    return bot

def send_fast_reply(chat_id, text):
    """دالة الرد السريع المباشر"""
    try:
        requests.post(TELEGRAM_API_URL, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}, timeout=5)
    except Exception as e:
        logging.error(f"Fast reply error: {e}")

def background_save(chat_id, title, chat_type):
    """حفظ البيانات في الخلفية"""
    try:
        chats_col.update_one(
            {"chat_id": str(chat_id)},
            {"$set": {"chat_id": str(chat_id), "title": title, "type": chat_type, "active": True, "last_seen": datetime.now()}},
            upsert=True
        )
    except: pass

def get_all_db_ids():
    """جلب كل الآيديات من قاعدة البيانات (للأدمن فقط)"""
    try:
        cursor = chats_col.find({"active": True})
        msg = "📂 **قائمة المشتركين في الداتا بايز:**\n\n"
        count = 0
        for doc in cursor:
            count += 1
            if count > 50: break # نكتفي بأول 50 لتجنب الرسائل الطويلة جداً
            msg += f"🔹 {doc.get('title', 'No Name')} | `{doc.get('chat_id')}`\n"
        msg += f"\n📊 العدد الإجمالي: {chats_col.count_documents({'active': True})}"
        return msg
    except Exception as e:
        return f"خطأ: {e}"

# --- دوال الإرسال المجدول ---
def send_to_all(content_type, content, caption=None):
    try:
        all_chats = [doc["chat_id"] for doc in chats_col.find({"active": True})]
        for chat_id in all_chats:
            async def task(cid=chat_id):
                try:
                    if content_type == "text": await get_bot().send_message(cid, content)
                    elif content_type == "photo": await get_bot().send_photo(cid, photo=content, caption=caption)
                except error.Forbidden: chats_col.update_one({"chat_id": cid}, {"$set": {"active": False}})
                except Exception: pass
            asyncio.run_coroutine_threadsafe(task(), event_loop)
            time.sleep(0.2) # فاصل زمني لتجنب الحظر
    except Exception as e:
        logging.error(f"Broadcast error: {e}")

# --- المجدول ---
def scheduler():
    while True:
        try:
            now = datetime.now(TIMEZONE)
            t, d = now.time(), now.date()
            def sent(k): return k in last_sent
            
            if t.hour == MORNING_TIME.hour and t.minute == MORNING_TIME.minute and not sent(f"m{d}"):
                send_to_all("photo", MORNING_IMG_URL, "🌅 أذكار الصباح"); last_sent[f"m{d}"] = True
            
            if t.hour == REMINDER_TIME_1.hour and t.minute == REMINDER_TIME_1.minute and not sent(f"r1{d}"):
                send_to_all("text", GENERAL_DHIKR); last_sent[f"r1{d}"] = True
            
            if t.hour == EVENING_TIME.hour and t.minute == EVENING_TIME.minute and not sent(f"e{d}"):
                send_to_all("photo", EVENING_IMG_URL, "🌇 أذكار المساء"); last_sent[f"e{d}"] = True
            
            if t.hour == REMINDER_TIME_2.hour and t.minute == REMINDER_TIME_2.minute and not sent(f"r2{d}"):
                send_to_all("text", GENERAL_DHIKR); last_sent[f"r2{d}"] = True
            
            if t.hour == REMINDER_TIME_3.hour and t.minute == REMINDER_TIME_3.minute and not sent(f"r3{d}"):
                send_to_all("text", GENERAL_DHIKR); last_sent[f"r3{d}"] = True
            
            if t.hour == NIGHT_TIME.hour and t.minute == NIGHT_TIME.minute and not sent(f"n{d}"):
                send_to_all("text", SLEEP_DHIKR); last_sent[f"n{d}"] = True
                
            time.sleep(60)
        except Exception as e:
            logging.error(f"Scheduler loop error: {e}")
            time.sleep(60)

threading.Thread(target=scheduler, daemon=True).start()

# --- الويب والاتصال ---
@app.route("/ping")
def ping(): return "pong"

def keep_alive():
    while True:
        try: requests.get(f"{WEBHOOK_URL.replace('/webhook', '')}/ping")
        except: pass
        time.sleep(600)
threading.Thread(target=keep_alive, daemon=True).start()

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    if not data: return jsonify(ok=True)

    # 1. كشف الإضافة لمجموعة
    if "my_chat_member" in data:
        update = data["my_chat_member"]
        if update["new_chat_member"]["status"] in ["member", "administrator"]:
            c = update["chat"]
            threading.Thread(target=background_save, args=(c["id"], c.get("title"), "group")).start()

    # 2. كشف الرسائل
    if "message" in data:
        msg = data["message"]
        chat = msg["chat"]
        user_id = msg.get("from", {}).get("id")
        text = msg.get("text", "").strip()
        command = text.split("@")[0]

        # حفظ المرسل في الخلفية
        threading.Thread(target=background_save, args=(chat["id"], chat.get("title", chat.get("first_name")), chat["type"])).start()

        # الرد السريع
        if command == "/start" and chat["type"] == "private":
            threading.Thread(target=send_fast_reply, args=(chat["id"], START_RESPONSE)).start()
        
        elif command == "/help" and chat["type"] == "private":
            threading.Thread(target=send_fast_reply, args=(chat["id"], "الأوامر:\n/start")).start()

        # أمر الآيدي (مطور للأدمن فقط)
        elif command == "/id":
            if user_id == ADMIN_ID:
                # إذا كنت الأدمن، يرسل لك قائمة المشتركين من الداتا بايز
                all_ids_text = get_all_db_ids()
                threading.Thread(target=send_fast_reply, args=(chat["id"], all_ids_text)).start()
            else:
                # إذا كان مستخدم عادي، يرسل له الآيدي الخاص به فقط
                threading.Thread(target=send_fast_reply, args=(chat["id"], f"🆔: `{chat['id']}`")).start()

        elif command == "/status" and user_id == ADMIN_ID:
            try:
                count = chats_col.count_documents({"active": True})
                t = datetime.now(TIMEZONE).strftime("%I:%M %p")
                threading.Thread(target=send_fast_reply, args=(chat["id"], f"✅ البوت متصل وسريع\n📊 المشتركين: {count}\n⏰ {t}")).start()
            except: pass

    return jsonify(ok=True)

if __name__ == "__main__":
    async def hook(): 
        try: await get_bot().set_webhook(WEBHOOK_URL)
        except: pass
    asyncio.run_coroutine_threadsafe(hook(), event_loop)
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
