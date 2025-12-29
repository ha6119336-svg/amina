import os, logging, asyncio, threading, time, requests
from datetime import datetime, time as dt_time
import pytz
from flask import Flask, request, jsonify
from telegram import Bot, error
import pymongo
from urllib.parse import quote_plus

# إعداد الـ Loop
event_loop = asyncio.new_event_loop()
def run_loop(loop): asyncio.set_event_loop(loop); loop.run_forever()
threading.Thread(target=run_loop, args=(event_loop,), daemon=True).start()

# --- إعدادات قاعدة البيانات (MongoDB) ---
RAW_PASSWORD = "mohamed862006&"
ESCAPED_PASSWORD = quote_plus(RAW_PASSWORD) 
MONGO_URL = f"mongodb+srv://mohamedabdellah:{ESCAPED_PASSWORD}@cluster0.hvuqzjx.mongodb.net/?appName=Cluster0"

try:
    client = pymongo.MongoClient(MONGO_URL)
    db = client["amina_db"]
    chats_col = db["chats"]
    logging.info("✅ تم الاتصال بقاعدة البيانات بنجاح")
except Exception as e:
    logging.error(f"❌ خطأ في الاتصال بقاعدة البيانات: {e}")

# --- الإعدادات ---
TELEGRAM_TOKEN = "8260168982:AAEy-YQDWa-yTqJKmsA_yeSuNtZb8qNeHAI"
ADMIN_ID = 7635779264
WEBHOOK_URL = "https://amina-3ryn.onrender.com/webhook"

# --- دالة نقل المجموعات القديمة (تعمل مرة واحدة وتتجاهل المكرر) ---
OLD_GROUPS_TO_MIGRATE = [
    "-1002225164483", "-1002576714713", "-1002704601167", 
    "-1003191159502", "-1003177076554", "-1002820782492"
]

def migrate_old_groups():
    count = 0
    for gid in OLD_GROUPS_TO_MIGRATE:
        try:
            result = chats_col.update_one(
                {"chat_id": gid},
                {"$set": {"chat_id": gid, "type": "group", "active": True, "migrated": True}},
                upsert=True
            )
            if result.upserted_id: count += 1
        except Exception as e:
            logging.error(f"Error migrating {gid}: {e}")
    if count > 0: logging.info(f"📦 تم نقل {count} مجموعة قديمة.")

threading.Thread(target=migrate_old_groups, daemon=True).start()

# --- روابط الصور ---
MORNING_IMG_URL = "https://raw.githubusercontent.com/ha6119336-svg/amina/main/photo_2025-12-22_10-05-15.jpg"
EVENING_IMG_URL = "https://raw.githubusercontent.com/ha6119336-svg/amina/main/photo_2025-12-28_16-54-02.jpg"

TIMEZONE = pytz.timezone("Africa/Algiers")

# --- المواعيد ---
MORNING_TIME = dt_time(8, 30)
EVENING_TIME = dt_time(16, 0)
NIGHT_TIME = dt_time(23, 0)
REMINDER_TIME_1 = dt_time(11, 0)
REMINDER_TIME_2 = dt_time(17, 0)
REMINDER_TIME_3 = dt_time(21, 0)

# --- النصوص ---
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

بارك الله فيكم 🌸
"""

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
bot, last_sent = None, {}

def get_bot():
    global bot
    if not bot: bot = Bot(token=TELEGRAM_TOKEN)
    return bot

# --- دوال قاعدة البيانات ---
def add_chat_to_db(chat_id, title=None, chat_type="private"):
    try:
        chats_col.update_one(
            {"chat_id": str(chat_id)},
            {"$set": {
                "chat_id": str(chat_id), 
                "title": title, 
                "type": chat_type, 
                "active": True,
                "last_seen": datetime.now()
            }},
            upsert=True
        )
        logging.info(f"➕ تم تحديث الشات: {chat_id}")
    except Exception as e:
        logging.error(f"Error adding chat: {e}")

def get_all_chats():
    try:
        return [doc["chat_id"] for doc in chats_col.find({"active": True})]
    except:
        return []

# --- الإرسال الجماعي ---
def send_to_all(content_type, content, caption=None):
    all_chats = get_all_chats()
    if not all_chats: return

    for chat_id in all_chats:
        async def task(cid=chat_id):
            try:
                if content_type == "text":
                    await get_bot().send_message(cid, content)
                elif content_type == "photo":
                    await get_bot().send_photo(cid, photo=content, caption=caption)
            except error.RetryAfter as e:
                time.sleep(int(e.retry_after) + 1)
                if content_type == "text": await get_bot().send_message(cid, content)
                else: await get_bot().send_photo(cid, photo=content, caption=caption)
            except error.Forbidden:
                chats_col.update_one({"chat_id": cid}, {"$set": {"active": False}})
            except Exception as e:
                logging.error(f"Error sending to {cid}: {e}")
        asyncio.run_coroutine_threadsafe(task(), event_loop)
        time.sleep(0.3)

# --- المجدول ---
def scheduler():
    while True:
        now = datetime.now(TIMEZONE)
        t, d = now.time(), now.date()
        def sent(k): return k in last_sent

        if t.hour == MORNING_TIME.hour and t.minute == MORNING_TIME.minute and not sent(f"m{d}"):
            send_to_all("photo", MORNING_IMG_URL, "🌅 أذكار الصباح")
            last_sent[f"m{d}"] = True

        if t.hour == REMINDER_TIME_1.hour and t.minute == REMINDER_TIME_1.minute and not sent(f"r1{d}"):
            send_to_all("text", GENERAL_DHIKR)
            last_sent[f"r1{d}"] = True

        if t.hour == EVENING_TIME.hour and t.minute == EVENING_TIME.minute and not sent(f"e{d}"):
            send_to_all("photo", EVENING_IMG_URL, "🌇 أذكار المساء")
            last_sent[f"e{d}"] = True

        if t.hour == REMINDER_TIME_2.hour and t.minute == REMINDER_TIME_2.minute and not sent(f"r2{d}"):
            send_to_all("text", GENERAL_DHIKR)
            last_sent[f"r2{d}"] = True

        if t.hour == REMINDER_TIME_3.hour and t.minute == REMINDER_TIME_3.minute and not sent(f"r3{d}"):
            send_to_all("text", GENERAL_DHIKR)
            last_sent[f"r3{d}"] = True

        if t.hour == NIGHT_TIME.hour and t.minute == NIGHT_TIME.minute and not sent(f"n{d}"):
            send_to_all("text", SLEEP_DHIKR)
            last_sent[f"n{d}"] = True

        time.sleep(60)

threading.Thread(target=scheduler, daemon=True).start()

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

    if "my_chat_member" in data:
        update = data["my_chat_member"]
        new_status = update["new_chat_member"]["status"]
        if new_status in ["member", "administrator"]:
            chat = update["chat"]
            add_chat_to_db(chat["id"], chat.get("title"), "group")

    if "message" in data:
        msg = data["message"]
        chat = msg["chat"]
        user_id = msg.get("from", {}).get("id")
        text = msg.get("text", "").strip()
        command = text.split("@")[0]

        add_chat_to_db(chat["id"], chat.get("title", chat.get("first_name")), chat["type"])

        if chat["type"] == "private":
            if command == "/start": send_message(chat["id"], START_RESPONSE)
            if command == "/help": send_message(chat["id"], "الأوامر:\n/start\n/id\n/status")
        
        if command == "/id":
             send_message(chat["id"], f"🆔: `{chat['id']}`")

        # 👇👇👇 التعديل هنا: الرد فقط إذا كان المرسل هو أنت (ADMIN_ID) 👇👇👇
        if command == "/status" and user_id == ADMIN_ID:
            try:
                count = chats_col.count_documents({"active": True})
                msg_text = f"✅ البوت يعمل ومتصل بقاعدة البيانات\n📊 عدد المشتركين النشطين: {count}\n⏰ {datetime.now(TIMEZONE)}"
                send_message(chat["id"], msg_text)
            except Exception as e:
                 send_message(chat["id"], f"⚠️ مشكلة في قاعدة البيانات: {e}")

    return jsonify(ok=True)

def send_message(chat_id, text):
    async def task():
        try: await get_bot().send_message(chat_id, text)
        except: pass
    asyncio.run_coroutine_threadsafe(task(), event_loop)

if __name__ == "__main__":
    async def hook(): 
        try:
            await get_bot().set_webhook(WEBHOOK_URL)
        except Exception as e:
            logging.error(f"Webhook Error: {e}")
            
    asyncio.run_coroutine_threadsafe(hook(), event_loop)
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
