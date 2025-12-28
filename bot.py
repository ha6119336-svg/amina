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
GROUPS = ["-1002225164483", "-1002576714713"]
WEBHOOK_URL = "https://amina-3ryn.onrender.com/webhook"

# --- روابط الصور (للصباح والمساء فقط) ---
MORNING_IMG_URL = "https://raw.githubusercontent.com/ha6119336-svg/amina/main/photo_2025-12-22_10-05-15.jpg"
EVENING_IMG_URL = "https://raw.githubusercontent.com/ha6119336-svg/amina/main/photo_2025-12-28_16-54-02.jpg"

TIMEZONE = pytz.timezone("Africa/Algiers")

# --- المواعيد (تم التعديل هنا) ---
MORNING_TIME = dt_time(8, 30)
EVENING_TIME = dt_time(17, 34)  # ✅ تم التعديل إلى 17:20
NIGHT_TIME = dt_time(23, 0)

# --- النصوص (أذكار النوم + الردود الأصلية) ---
SLEEP_DHIKR = """🌙 نام وأنت مغفور الذنب

قال رسول الله ﷺ:
"من قال حين يأوي إلى فراشه:
'لا إله إلا الله وحده لا شريك له، له الملك وله الحمد، وهو على كل شيء قدير، لا حول ولا قوة إلا بالله، سبحان الله والحمد لله ولا إله إلا الله والله أكبر'

غفر الله ذنوبه أو خطاياه وإن كانت مثل زبد البحر." 🤎🌗"""

START_RESPONSE = """🤖 بوت أذكار الصباح والمساء

🌅 يرسل أذكار الصباح
🌇 يرسل أذكار المساء
🌙 يرسل أذكار النوم

⏰ المواعيد:
• 08:30 صباحاً
• 17:20 مساءً
• 23:00 ليلاً

👤 حساب المطوّر:
@Mik_emm

💡 صاحب الفكرة:
@mohamedelhocine
🤲 نرجو الدعاء له

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

# دالة لإرسال النصوص (تستخدم للنوم وللأوامر)
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

# دالة لإرسال الصور (تستخدم للصباح والمساء)
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

        # الصباح (صورة)
        if t.hour == MORNING_TIME.hour and t.minute == MORNING_TIME.minute and not sent(f"m{d}"):
            for g in GROUPS: 
                send_photo(g, MORNING_IMG_URL, caption="🌅 أذكار الصباح")
                time.sleep(1)
            last_sent[f"m{d}"] = True

        # المساء (صورة) - التوقيت الجديد 17:20
        if t.hour == EVENING_TIME.hour and t.minute == EVENING_TIME.minute and not sent(f"e{d}"):
            for g in GROUPS: 
                send_photo(g, EVENING_IMG_URL, caption="🌇 أذكار المساء")
                time.sleep(1)
            last_sent[f"e{d}"] = True

        # النوم (نص كتابة)
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
    if not data or "message" not in data: return jsonify(ok=True)
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
