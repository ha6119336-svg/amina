import os
import logging
import asyncio
import threading
import time
import requests
from datetime import datetime, time as dt_time
import pytz
from flask import Flask, request, jsonify
from telegram import Bot, error
from dotenv import load_dotenv

# تحميل المتغيرات من ملف .env
load_dotenv()

# إعداد الـ Loop
event_loop = asyncio.new_event_loop()
def run_loop(loop): 
    asyncio.set_event_loop(loop)
    loop.run_forever()
threading.Thread(target=run_loop, args=(event_loop,), daemon=True).start()

# --- الإعدادات ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = 7635779264 

# ✅ قائمة المجموعات والقنوات (تم الإبقاء على كافة الآيديات السابقة)
GROUPS = [
    "-1002225164483", "-1003052347212", "-1003323851379", "-1002900824077", 
    "-1002266393691", "-1003370258674", "-1003044484309", "-1002196247994", 
    "-1003153665259", "-1001978444680", "-1002945924752", "-1002830014765", 
    "-1002277708600", "-1002576714713", "-1003372233969", "-1002704601167", 
    "-1003191159502", "-1003177076554", "-1002820782492", "-1002489850528",
    "-1003649220499", "-1003031738078", "-1003205832373", "-1003186786281", 
    "-1003189260339"
]

WEBHOOK_URL = "https://amina-3ryn.onrender.com/webhook"

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
GENERAL_DHIKR = """🌿 **﴿ وَاذْكُر ربّكَ إِذَا نَسِيتَ ﴾**

  سُبحان الله
  الحمدلله
  الله أكبر
  أستغفر الله
  لا إله إلا الله
  لا حول ولا قوة إلا بالله
  سُبحان الله وبحمده
  سُبحان الله العظيم
  اللَّهُمَّ صلِّ وسلِم على نبينا محمد
  لا إله إلا أنت سُبحانك إني كنت من الظالمين
"""

SLEEP_DHIKR = """🌙 نام وأنت مغفور الذنب

قال رسول الله ﷺ:
"من قال حين يأوي إلى فراشه:
'لا إله إلا الله وحده لا شريك له، له الملك وله الحمد، وهو على كل شيء قدير، لا حول ولا قوة إلا بالله، سبحان الله والحمد لله ولا إله إلا الله والله أكبر'

غفر الله ذنوبه أو خطاياه وإن كانت مثل زبد البحر." 🤎🌗"""

START_RESPONSE = """🤖 بوت أذكار الصباح والمساء

يُرسل الأذكار والتذكيرات يومياً   (للمجموعات والقنوات):

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

def send_message(chat_id, text):
    async def task():
        try:
            await get_bot().send_message(chat_id, text, parse_mode="Markdown")
        except error.RetryAfter as e:
            await asyncio.sleep(e.retry_after)
            await get_bot().send_message(chat_id, text, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Error sending message to {chat_id}: {e}")
    asyncio.run_coroutine_threadsafe(task(), event_loop)

def send_photo(chat_id, photo_url, caption=None):
    async def task():
        try:
            await get_bot().send_photo(chat_id=chat_id, photo=photo_url, caption=caption)
        except error.RetryAfter as e:
            await asyncio.sleep(e.retry_after)
            await get_bot().send_photo(chat_id=chat_id, photo=photo_url, caption=caption)
        except Exception as e:
            logging.error(f"Error sending photo to {chat_id}: {e}")
    asyncio.run_coroutine_threadsafe(task(), event_loop)

def scheduler():
    while True:
        now = datetime.now(TIMEZONE)
        t, d = now.time(), now.date()
        def sent(k): return k in last_sent

        # العمليات المجدولة لكل المعرفات في GROUPS (سواء كانت مجموعات أو قنوات)
        if t.hour == MORNING_TIME.hour and t.minute == MORNING_TIME.minute and not sent(f"m{d}"):
            for g in GROUPS: send_photo(g, MORNING_IMG_URL, caption="🌅 أذكار الصباح")
            last_sent[f"m{d}"] = True

        if t.hour == REMINDER_TIME_1.hour and t.minute == REMINDER_TIME_1.minute and not sent(f"r1{d}"):
            for g in GROUPS: send_message(g, GENERAL_DHIKR)
            last_sent[f"r1{d}"] = True

        if t.hour == EVENING_TIME.hour and t.minute == EVENING_TIME.minute and not sent(f"e{d}"):
            for g in GROUPS: send_photo(g, EVENING_IMG_URL, caption="🌇 أذكار المساء")
            last_sent[f"e{d}"] = True

        if t.hour == REMINDER_TIME_2.hour and t.minute == REMINDER_TIME_2.minute and not sent(f"r2{d}"):
            for g in GROUPS: send_message(g, GENERAL_DHIKR)
            last_sent[f"r2{d}"] = True

        if t.hour == REMINDER_TIME_3.hour and t.minute == REMINDER_TIME_3.minute and not sent(f"r3{d}"):
            for g in GROUPS: send_message(g, GENERAL_DHIKR)
            last_sent[f"r3{d}"] = True

        if t.hour == NIGHT_TIME.hour and t.minute == NIGHT_TIME.minute and not sent(f"n{d}"):
            for g in GROUPS: send_message(g, SLEEP_DHIKR)
            last_sent[f"n{d}"] = True

        time.sleep(30)

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

    # ✅ تحديث: كشف الانضمام للقنوات والمجموعات معاً
    target_update = data.get("my_chat_member") or data.get("chat_member")
    if target_update:
        new_status = target_update.get("new_chat_member", {}).get("status")
        if new_status in ["member", "administrator"]:
            chat = target_update["chat"]
            title = chat.get("title", "No Title")
            cid = chat["id"]
            ctype = chat.get("type", "unknown")
            msg_to_admin = f"🔔 **تم دخول {ctype} جديدة!**\n\n🏷 الاسم: {title}\n🆔 الآيدي: `{cid}`"
            send_message(ADMIN_ID, msg_to_admin)

    # معالجة الرسائل العادية
    if "message" in data:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        chat_type = msg["chat"]["type"]
        user_id = msg.get("from", {}).get("id")
        text = msg.get("text", "").strip()
        command = text.split("@")[0]

        if chat_type == "private" or user_id == ADMIN_ID:
            if command == "/start": send_message(chat_id, START_RESPONSE)
            elif command == "/help": send_message(chat_id, HELP_RESPONSE)
            elif command == "/status":
                send_message(chat_id, f"✅ البوت يعمل\n⏰ {datetime.now(TIMEZONE).strftime('%H:%M:%S')}")

    return jsonify(ok=True)

if __name__ == "__main__":
    async def hook(): 
        try: await get_bot().set_webhook(WEBHOOK_URL)
        except Exception as e: logging.error(f"Webhook Error: {e}")
    asyncio.run_coroutine_threadsafe(hook(), event_loop)
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
