import os, logging, asyncio, threading, time, requests
from datetime import datetime, time as dt_time
import pytz
from flask import Flask, request, jsonify
from telegram import Bot, error

# إعداد الـ Loop
event_loop = asyncio.new_event_loop()
def run_loop(loop): asyncio.set_event_loop(loop); loop.run_forever()
threading.Thread(target=run_loop, args=(event_loop,), daemon=True).start()

# --- الإعدادات ---
TELEGRAM_TOKEN = "8260168982:AAEy-YQDWa-yTqJKmsA_yeSuNtZb8qNeHAI"
ADMIN_ID = 7635779264

# ✅ قائمة المجموعات (كما طلبتها)
GROUPS = ["-1002225164483", "-1002576714713", "-1002704601167", "-1003191159502", "-1003177076554", "-1002820782492", "-1002489850528","-1003649220499", "-1003031738078", "-1003205832373", "-1003186786281", "-1003189260339"]

WEBHOOK_URL = "https://amina-3ryn.onrender.com/webhook"

# --- روابط الصور ---
MORNING_IMG_URL = "https://raw.githubusercontent.com/ha6119336-svg/amina/main/photo_2025-12-22_10-05-15.jpg"
EVENING_IMG_URL = "https://raw.githubusercontent.com/ha6119336-svg/amina/main/photo_2025-12-28_16-54-02.jpg"

TIMEZONE = pytz.timezone("Africa/Algiers")

# --- المواعيد ---
# 1. المواعيد الأساسية
MORNING_TIME = dt_time(8, 30)   # أذكار الصباح (صورة)
EVENING_TIME = dt_time(16, 0)   # أذكار المساء (صورة)
NIGHT_TIME = dt_time(23, 0)     # أذكار النوم (نص)

# 2. مواعيد الذكر العام (النص الكتابي)
REMINDER_TIME_1 = dt_time(11, 0)  # 11 صباحاً
REMINDER_TIME_2 = dt_time(17, 0)  # 5 مساءً
REMINDER_TIME_3 = dt_time(21, 0)  # 9 ليلاً

# --- النصوص ---

# الذكر العام (وذكر ربك إذا نسيت)
GENERAL_DHIKR = """🌿 **﴿ وَاذْكُر ربّكَ إِذَا نَسِيتَ ﴾**

✨ سُبحان الله
✨ الحمدلله
✨ الله أكبر
✨ أستغفر الله
✨ لا إله إلا الله
✨ لا حول ولا قوة إلا بالله
✨ سُبحان الله وبحمده
✨ سُبحان الله العظيم
✨ اللَّهُمَّ صلِّ وسلِم على نبينا محمد
✨ لا إله إلا أنت سُبحانك إني كنت من الظالمين
"""

# أذكار النوم
SLEEP_DHIKR = """🌙 نام وأنت مغفور الذنب

قال رسول الله ﷺ:
"من قال حين يأوي إلى فراشه:
'لا إله إلا الله وحده لا شريك له، له الملك وله الحمد، وهو على كل شيء قدير، لا حول ولا قوة إلا بالله، سبحان الله والحمد لله ولا إله إلا الله والله أكبر'

غفر الله ذنوبه أو خطاياه وإن كانت مثل زبد البحر." 🤎🌗"""

# رسالة البداية
START_RESPONSE = """🤖 بوت أذكار الصباح والمساء

يُرسل الأذكار والتذكيرات يومياً بتوقيت الجزائر:

🌅 08:30 | أذكار الصباح  
📿 11:00 | تذكير بالله  
🌇 16:00 | أذكار المساء  
📿 17:00 | تذكير بالله  
📿 21:00 | تذكير بالله   
🌙 23:00 | أذكار النوم  

👤 حساب المطوّر:
@Mik_emm

💡 صاحب الفكرة:
@mohamedelhocine
🤲 نرجو الدعاء له
واي شخص عنده افكار او اضافات للبوت يتصل بي وشكرا 
بارك الله فيكم 🌸
"""

HELP_RESPONSE = """📌 الأوامر المتاحة:
/start - معلومات البوت
/help - المساعدة
/status - حالة البوت
"""

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
bot, last_sent = None, {}

def get_bot():
    global bot
    if not bot: bot = Bot(token=TELEGRAM_TOKEN)
    return bot

# دالة لإرسال النصوص
def send_message(chat_id, text):
    async def task():
        try:
            await get_bot().send_message(chat_id, text)
        except error.RetryAfter as e:
            time.sleep(int(e.retry_after) + 1)
            await get_bot().send_message(chat_id, text)
        except Exception as e:
            logging.error(f"Error sending message: {e}")
            
    asyncio.run_coroutine_threadsafe(task(), event_loop)

# دالة لإرسال الصور
def send_photo(chat_id, photo_url, caption=None):
    async def task():
        try:
            await get_bot().send_photo(chat_id=chat_id, photo=photo_url, caption=caption)
        except error.RetryAfter as e:
            time.sleep(int(e.retry_after) + 1)
            await get_bot().send_photo(chat_id=chat_id, photo=photo_url, caption=caption)
        except Exception as e:
            logging.error(f"Error sending photo to {chat_id}: {e}")

    asyncio.run_coroutine_threadsafe(task(), event_loop)

def scheduler():
    while True:
        now = datetime.now(TIMEZONE)
        t, d = now.time(), now.date()
        def sent(k): return k in last_sent

        # 1. أذكار الصباح (صورة) - 08:30
        if t.hour == MORNING_TIME.hour and t.minute == MORNING_TIME.minute and not sent(f"m{d}"):
            for g in GROUPS: 
                send_photo(g, MORNING_IMG_URL, caption="🌅 أذكار الصباح")
                time.sleep(1)
            last_sent[f"m{d}"] = True

        # 2. التذكير الأول (نص) - 11:00
        if t.hour == REMINDER_TIME_1.hour and t.minute == REMINDER_TIME_1.minute and not sent(f"r1{d}"):
            for g in GROUPS: 
                send_message(g, GENERAL_DHIKR)
                time.sleep(1)
            last_sent[f"r1{d}"] = True

        # 3. أذكار المساء (صورة) - 16:00
        if t.hour == EVENING_TIME.hour and t.minute == EVENING_TIME.minute and not sent(f"e{d}"):
            for g in GROUPS: 
                send_photo(g, EVENING_IMG_URL, caption="🌇 أذكار المساء")
                time.sleep(1)
            last_sent[f"e{d}"] = True

        # 4. التذكير الثاني (نص) - 17:00
        if t.hour == REMINDER_TIME_2.hour and t.minute == REMINDER_TIME_2.minute and not sent(f"r2{d}"):
            for g in GROUPS: 
                send_message(g, GENERAL_DHIKR)
                time.sleep(1)
            last_sent[f"r2{d}"] = True

        # 5. التذكير الثالث (نص) - 21:00
        if t.hour == REMINDER_TIME_3.hour and t.minute == REMINDER_TIME_3.minute and not sent(f"r3{d}"):
            for g in GROUPS: 
                send_message(g, GENERAL_DHIKR)
                time.sleep(1)
            last_sent[f"r3{d}"] = True

        # 6. أذكار النوم (نص) - 23:00
        if t.hour == NIGHT_TIME.hour and t.minute == NIGHT_TIME.minute and not sent(f"n{d}"):
            for g in GROUPS: 
                send_message(g, SLEEP_DHIKR)
                time.sleep(1)
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

    # 1. ✅ الإضافة الجديدة: كشف دخول مجموعة وإرسال الآيدي للأدمن
    if "my_chat_member" in data:
        update = data["my_chat_member"]
        new_status = update.get("new_chat_member", {}).get("status")
        
        if new_status in ["member", "administrator"]:
            chat = update["chat"]
            title = chat.get("title", "No Title")
            cid = chat["id"]
            
            # إرسال التنبيه لك
            msg_to_admin = f"🔔 **تم دخول مجموعة جديدة!**\n\n🏷 الاسم: {title}\n🆔 الآيدي: `{cid}`"
            send_message(ADMIN_ID, msg_to_admin)

    # 2. معالجة الرسائل العادية (ستارت، هيلب...)
    if "message" in data:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        chat_type = msg["chat"]["type"]
        user_id = msg.get("from", {}).get("id")
        text = msg.get("text", "").strip()
        command = text.split("@")[0]

        if chat_type == "private" or user_id == ADMIN_ID:
            if command == "/start": send_message(chat_id, START_RESPONSE)
            if command == "/help": send_message(chat_id, HELP_RESPONSE)
            if command == "/status":
                send_message(chat_id, f"✅ البوت يعمل\n⏰ {datetime.now(TIMEZONE)}")

    return jsonify(ok=True)

if __name__ == "__main__":
    async def hook(): 
        try:
            await get_bot().set_webhook(WEBHOOK_URL)
        except Exception as e:
            logging.error(f"Webhook Error: {e}")
            
    asyncio.run_coroutine_threadsafe(hook(), event_loop)
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
