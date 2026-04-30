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

load_dotenv()

event_loop = asyncio.new_event_loop()
def run_loop(loop): asyncio.set_event_loop(loop); loop.run_forever()
threading.Thread(target=run_loop, args=(event_loop,), daemon=True).start()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    print("⚠️ Error: TELEGRAM_TOKEN is missing!")

ADMIN_ID = 7635779264 

GROUPS = [
   "-1002576714713"
]

TARGET_GROUP = -1002945924752
THREAD_ID = 8017

WEBHOOK_URL = "https://amina-3ryn.onrender.com/webhook"

MORNING_IMG_URL = "https://raw.githubusercontent.com/ha6119336-svg/amina/main/photo_2025-12-22_10-05-15.jpg"
EVENING_IMG_URL = "https://raw.githubusercontent.com/ha6119336-svg/amina/main/photo_2025-12-28_16-54-02.jpg"

# الجمعة
JUMUAH_IMG_URL = "https://raw.githubusercontent.com/ha6119336-svg/amina/main/images.jpeg"
KAHF_PDF_URL = "https://raw.githubusercontent.com/ha6119336-svg/amina/main/kahf.pdf"
JUMUAH_TIME = dt_time(1,0 )

# 🔥 هامش
WINDOW = 10

TIMEZONE = pytz.timezone("Africa/Algiers")

MORNING_TIME = dt_time(8, 30)
EVENING_TIME = dt_time(16, 0)
NIGHT_TIME = dt_time(1,2)
REMINDER_TIME_1 = dt_time(11, 0)
REMINDER_TIME_2 = dt_time(17, 0)
REMINDER_TIME_3 = dt_time(1, 1)

GENERAL_DHIKR = """ 🌿 **﴿ وَاذْكُر ربّكَ إِذَا نَسِيتَ ﴾**

  سُبحان الله
  الحمدلله
  الله أكبر
  أستغفر الله
  لا إله إلا الله
  لا حول ولا قوة إلا بالله
  سُبحان الله وبحمده
  سُبحان الله العظيم
  اللَّهُمَّ صلِّ وسلِم على نبينا محمد
  لا إله إلا أنت سُبحانك إني كنت من الظالمين.
"""

SLEEP_DHIKR = """🌙 نام وأنت مغفور الذنب

قال رسول الله ﷺ:
"من قال حين يأوي إلى فراشه:
'لا إله إلا الله وحده لا شريك له، له الملك وله الحمد، وهو على كل شيء قدير، لا حول ولا قوة إلا بالله، سبحان الله والحمد لله ولا إله إلا الله والله أكبر'

غفر الله ذنوبه أو خطاياه وإن كانت مثل زبد البحر." 🤎🌗"""

START_RESPONSE = """🤖 بوت أذكار الصباح والمساء

يُرسل الأذكار والتذكيرات يومياً بتوقيت الجزائر:

🌅 08:30 | أذكار الصباح  
📿 11:00 | تذكير بالله  
🌇 16:00 | أذكار المساء  
📿 17:00 | تذكير بالله  
📿 21:00 | تذكير بالله   
🌙 23:00 | أذكار النوم  
"""

HELP_RESPONSE = """📌 الأوامر:
/start
/help
/status
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
            if int(chat_id) == TARGET_GROUP:
                await get_bot().send_message(chat_id, text, message_thread_id=THREAD_ID)
            else:
                await get_bot().send_message(chat_id, text)
        except Exception as e:
            logging.error(e)
    asyncio.run_coroutine_threadsafe(task(), event_loop)

def send_photo(chat_id, photo_url, caption=None):
    async def task():
        try:
            if int(chat_id) == TARGET_GROUP:
                await get_bot().send_photo(chat_id=chat_id, photo=photo_url, caption=caption, message_thread_id=THREAD_ID)
            else:
                await get_bot().send_photo(chat_id=chat_id, photo=photo_url, caption=caption)
        except Exception as e:
            logging.error(e)
    asyncio.run_coroutine_threadsafe(task(), event_loop)

def send_document(chat_id, file_url, caption=None):
    async def task():
        try:
            if int(chat_id) == TARGET_GROUP:
                await get_bot().send_document(chat_id=chat_id, document=file_url, caption=caption, message_thread_id=THREAD_ID)
            else:
                await get_bot().send_document(chat_id=chat_id, document=file_url, caption=caption)
        except Exception as e:
            logging.error(e)
    asyncio.run_coroutine_threadsafe(task(), event_loop)

def scheduler():
    while True:
        now = datetime.now(TIMEZONE)
        t, d = now.time(), now.date()
        def sent(k): return k in last_sent

        if t.hour == MORNING_TIME.hour and MORNING_TIME.minute <= t.minute <= MORNING_TIME.minute + WINDOW and not sent(f"m{d}"):
            for g in GROUPS:
                send_photo(g, MORNING_IMG_URL, caption="🌅 أذكار الصباح")
                time.sleep(0.3)
            last_sent[f"m{d}"] = True

        if t.hour == REMINDER_TIME_1.hour and REMINDER_TIME_1.minute <= t.minute <= REMINDER_TIME_1.minute + WINDOW and not sent(f"r1{d}"):
            for g in GROUPS:
                send_message(g, GENERAL_DHIKR)
                time.sleep(0.3)
            last_sent[f"r1{d}"] = True

        if t.hour == EVENING_TIME.hour and EVENING_TIME.minute <= t.minute <= EVENING_TIME.minute + WINDOW and not sent(f"e{d}"):
            for g in GROUPS:
                send_photo(g, EVENING_IMG_URL, caption="🌇 أذكار المساء")
                time.sleep(0.3)
            last_sent[f"e{d}"] = True

        if t.hour == REMINDER_TIME_2.hour and REMINDER_TIME_2.minute <= t.minute <= REMINDER_TIME_2.minute + WINDOW and not sent(f"r2{d}"):
            for g in GROUPS:
                send_message(g, GENERAL_DHIKR)
                time.sleep(0.3)
            last_sent[f"r2{d}"] = True

        if t.hour == REMINDER_TIME_3.hour and REMINDER_TIME_3.minute <= t.minute <= REMINDER_TIME_3.minute + WINDOW and not sent(f"r3{d}"):
            for g in GROUPS:
                send_message(g, GENERAL_DHIKR)
                time.sleep(0.3)
            last_sent[f"r3{d}"] = True

        if t.hour == NIGHT_TIME.hour and NIGHT_TIME.minute <= t.minute <= NIGHT_TIME.minute + WINDOW and not sent(f"n{d}"):
            for g in GROUPS:
                send_message(g, SLEEP_DHIKR)
                time.sleep(0.3)
            last_sent[f"n{d}"] = True

        # الجمعة
        if now.weekday() == 4 and not sent(f"j{d}"):
            if t.hour == JUMUAH_TIME.hour and JUMUAH_TIME.minute <= t.minute <= JUMUAH_TIME.minute + WINDOW:
                for g in GROUPS:
                    send_photo(g, JUMUAH_IMG_URL, caption="🕌 سنن يوم الجمعة")
                    time.sleep(0.3)
                    send_document(g, KAHF_PDF_URL, caption="📖 سورة الكهف")
                    time.sleep(0.3)
                last_sent[f"j{d}"] = True

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

    if "message" in data:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text","")

        if text == "/start":
            send_message(chat_id, START_RESPONSE)
        elif text == "/help":
            send_message(chat_id, HELP_RESPONSE)

    return jsonify(ok=True)

if __name__ == "__main__":
    async def hook():
        await get_bot().set_webhook(WEBHOOK_URL)

    asyncio.run_coroutine_threadsafe(hook(), event_loop)

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
