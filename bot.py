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

# ========== إعدادات البوت الأساسية ==========
event_loop = asyncio.new_event_loop()
def run_loop(loop): asyncio.set_event_loop(loop); loop.run_forever()
threading.Thread(target=run_loop, args=(event_loop,), daemon=True).start()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    print("⚠️ Error: TELEGRAM_TOKEN is missing!")

ADMIN_ID = 7635779264 

GROUPS = [" -1002576714713"]

WEBHOOK_URL = "https://amina-3ryn.onrender.com/webhook"

MORNING_IMG_URL = "https://raw.githubusercontent.com/ha6119336-svg/amina/main/photo_2025-12-22_10-05-15.jpg"
EVENING_IMG_URL = "https://raw.githubusercontent.com/ha6119336-svg/amina/main/photo_2025-12-28_16-54-02.jpg"

TIMEZONE = pytz.timezone("Africa/Algiers")

MORNING_TIME = dt_time(8, 30)
EVENING_TIME = dt_time(16, 0)
NIGHT_TIME = dt_time(23, 0)
REMINDER_TIME_1 = dt_time(11, 0)
REMINDER_TIME_2 = dt_time(17, 0)
REMINDER_TIME_3 = dt_time(21, 0)

# وقت التفسير
QURAN_TIME = dt_time(16,59)

GENERAL_DHIKR = """ 🌿 ﴿ وَاذْكُر ربّكَ إِذَا نَسِيتَ ﴾

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
📖 14:43 | تفسير القرآن

👤 حسابي  :
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

# ========== متغيرات التفسير ==========
SURAH_ORDER = list(range(114, 92, -1))  # من الناس (114) إلى الضحى (93)
current_surah_index = 0

def get_bot():
    global bot
    if not bot: bot = Bot(token=TELEGRAM_TOKEN)
    return bot

def send_message(chat_id, text):
    async def task():
        try:
            await get_bot().send_message(chat_id, text, parse_mode='HTML')
        except error.RetryAfter as e:
            time.sleep(int(e.retry_after) + 1)
            await get_bot().send_message(chat_id, text, parse_mode='HTML')
        except Exception as e:
            logging.error(f"Error sending message: {e}")
    asyncio.run_coroutine_threadsafe(task(), event_loop)

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

def send_long_message(chat_id, text):
    """إرسال رسائل طويلة مقسمة"""
    if len(text) <= 4096:
        send_message(chat_id, text)
        return
    
    parts = []
    current_part = ""
    for line in text.split('\n'):
        if len(current_part) + len(line) + 1 > 4000:
            parts.append(current_part)
            current_part = line + '\n'
        else:
            current_part += line + '\n'
    if current_part:
        parts.append(current_part)
    
    for i, part in enumerate(parts):
        if i == 0:
            send_message(chat_id, part)
        else:
            send_message(chat_id, f"<b>تابع...</b>\n\n{part}")
        time.sleep(1)

# ========== دوال التفسير المحسنة ==========

def get_surah_info(surah_num):
    """جلب معلومات السورة"""
    try:
        response = requests.get(f"https://api.alquran.cloud/v1/surah/{surah_num}", timeout=10)
        response.raise_for_status()
        data = response.json()["data"]
        revelation_type = "مكية" if data["revelationType"] == "Meccan" else "مدنية"
        return {
            "name": data["name"],
            "total_ayahs": data["numberOfAyahs"],
            "revelation_type": revelation_type,
            "order": data["number"]
        }
    except Exception as e:
        logging.error(f"خطأ في جلب معلومات السورة: {e}")
        return None

def get_full_surah_text_and_tafsir(surah_num):
    """
    جلب نص السورة كاملة مع التفسير الميسر لكل آية
    يعتمد على الترتيب (Index) لضمان مطابقة التفسير مع الآية الصحيحة
    """
    try:
        # 1. جلب نص السورة
        response = requests.get(f"https://api.alquran.cloud/v1/surah/{surah_num}", timeout=10)
        response.raise_for_status()
        surah_data = response.json()["data"]
        
        # 2. جلب التفسير الميسر
        tafsir_url = f"https://quranenc.com/api/v1/translation/sura/arabic_moyassar/{surah_num}"
        tafsir_response = requests.get(tafsir_url, timeout=15)
        
        verses = {}
        
        # إنشاء هيكل الآيات أولاً
        for ayah in surah_data["ayahs"]:
            num = ayah["numberInSurah"]
            verses[num] = {"text": ayah["text"], "tafsir": ""}

        # 3. دمج التفسير بدقة - نعتمد على الترتيب (Index) لضمان المطابقة
        if tafsir_response.status_code == 200:
            t_data = tafsir_response.json().get("result", [])
            for index, item in enumerate(t_data):
                actual_num = index + 1  # رقم الآية داخل السورة (يبدأ من 1)
                explanation = item.get("translation", "").strip()
                
                if actual_num in verses:
                    verses[actual_num]["tafsir"] = explanation

        return verses, surah_data["name"], surah_data["numberOfAyahs"]
        
    except Exception as e:
        logging.error(f"Error in fetching Quran data: {e}")
        return None, None, None

def send_quran_to_all_groups():
    """إرسال السورة كاملة لجميع المجموعات في وقت واحد"""
    global current_surah_index
    
    if current_surah_index >= len(SURAH_ORDER):
        current_surah_index = 0
        logging.info("🔄 تم الانتهاء من جميع السور، نبدأ من جديد")
    
    surah_num = SURAH_ORDER[current_surah_index]
    verses, surah_name, total_ayahs = get_full_surah_text_and_tafsir(surah_num)
    
    if not verses:
        for g in GROUPS:
            send_message(g, f"❌ خطأ في جلب سورة {surah_num}")
        return
    
    # جلب معلومات السورة
    surah_info = get_surah_info(surah_num)
    revelation_type = surah_info["revelation_type"] if surah_info else "مكية"
    
    logging.info(f"📖 جاري إرسال سورة {surah_name} إلى {len(GROUPS)} مجموعة...")
    
    # ========== بناء الرسالة الأولى: معلومات + نص السورة ==========
    header = f"""🌟 <b>سورة {surah_name}</b>
━━━━━━━━━━━━━━━━━━━━━
📊 رقم السورة: {surah_num}
📖 عدد الآيات: {total_ayahs}
📍 نوع السورة: {revelation_type}
━━━━━━━━━━━━━━━━━━━━━

<b>نص السورة:</b>\n\n"""
    
    # بناء نص السورة
    surah_text = ""
    for i in range(1, total_ayahs + 1):
        if i in verses:
            surah_text += f"{verses[i]['text']}\n\n"
    
    surah_message = header + surah_text
    
    # ========== بناء الرسالة الثانية: التفسير بالشكل المطلوب ==========
    tafsir_header = f"📚 <b>تفسير سورة {surah_name}</b>\n"
    tafsir_header += "<b>التفسير الميسر</b>\n"
    tafsir_header += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    tafsir_text = tafsir_header
    
    for i in range(1, total_ayahs + 1):
        if i in verses:
            ayah_text = verses[i]["text"]
            ayah_tafsir = verses[i]["tafsir"]
            
            # التنسيق: الآية ثم التفسير
            tafsir_text += f"﴿ {ayah_text} ﴾\n"
            
            if ayah_tafsir:
                tafsir_text += f"<b>• تفسير الآية {i}:</b>\n"
                tafsir_text += f"{ayah_tafsir}\n"
            else:
                tafsir_text += f"<b>• الآية {i}:</b> [يُرجى مراجعة التفسير مباشرة]\n"
            
            tafsir_text += "───\n\n"
    
    # ========== إرسال الرسائل لجميع المجموعات ==========
    for g in GROUPS:
        try:
            # الرسالة الأولى: نص السورة
            send_long_message(g, surah_message)
            time.sleep(2)
            
            # الرسالة الثانية: التفسير
            send_long_message(g, tafsir_text)
            time.sleep(1)
            
            logging.info(f"✅ تم إرسال سورة {surah_name} إلى المجموعة {g}")
        except Exception as e:
            logging.error(f"خطأ في إرسال سورة {surah_name} إلى {g}: {e}")
    
    # تحديث المؤشر للسورة القادمة
    current_surah_index += 1
    remaining = len(SURAH_ORDER) - current_surah_index
    logging.info(f"📊 السور المتبقية: {remaining}")

# ========== الـ Scheduler ==========

def scheduler():
    while True:
        now = datetime.now(TIMEZONE)
        t, d = now.time(), now.date()
        def sent(k): return k in last_sent

        if t.hour == MORNING_TIME.hour and t.minute == MORNING_TIME.minute and not sent(f"m{d}"):
            for g in GROUPS: 
                send_photo(g, MORNING_IMG_URL, caption="🌅 أذكار الصباح")
                time.sleep(1)
            last_sent[f"m{d}"] = True

        if t.hour == REMINDER_TIME_1.hour and t.minute == REMINDER_TIME_1.minute and not sent(f"r1{d}"):
            for g in GROUPS: 
                send_message(g, GENERAL_DHIKR)
                time.sleep(1)
            last_sent[f"r1{d}"] = True

        if t.hour == EVENING_TIME.hour and t.minute == EVENING_TIME.minute and not sent(f"e{d}"):
            for g in GROUPS: 
                send_photo(g, EVENING_IMG_URL, caption="🌇 أذكار المساء")
                time.sleep(1)
            last_sent[f"e{d}"] = True

        if t.hour == REMINDER_TIME_2.hour and t.minute == REMINDER_TIME_2.minute and not sent(f"r2{d}"):
            for g in GROUPS: 
                send_message(g, GENERAL_DHIKR)
                time.sleep(1)
            last_sent[f"r2{d}"] = True

        if t.hour == REMINDER_TIME_3.hour and t.minute == REMINDER_TIME_3.minute and not sent(f"r3{d}"):
            for g in GROUPS: 
                send_message(g, GENERAL_DHIKR)
                time.sleep(1)
            last_sent[f"r3{d}"] = True

        if t.hour == NIGHT_TIME.hour and t.minute == NIGHT_TIME.minute and not sent(f"n{d}"):
            for g in GROUPS: 
                send_message(g, SLEEP_DHIKR)
                time.sleep(1)
            last_sent[f"n{d}"] = True

        # وقت التفسير
        if t.hour == QURAN_TIME.hour and t.minute == QURAN_TIME.minute and not sent(f"q{d}"):
            send_quran_to_all_groups()
            last_sent[f"q{d}"] = True

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
        new_status = update.get("new_chat_member", {}).get("status")
        
        if new_status in ["member", "administrator"]:
            chat = update["chat"]
            title = chat.get("title", "No Title")
            cid = chat["id"]
            msg_to_admin = f"🔔 تم دخول مجموعة جديدة!\n\n🏷 الاسم: {title}\n🆔 الآيدي: {cid}"
            send_message(ADMIN_ID, msg_to_admin)

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
