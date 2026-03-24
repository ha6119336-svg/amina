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

GROUPS = ["-1002576714713"]

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
QURAN_TIME = dt_time(16, 15)

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

def get_full_surah_text(surah_num):
    """جلب نص السورة كاملة"""
    try:
        response = requests.get(f"https://api.alquran.cloud/v1/surah/{surah_num}", timeout=10)
        response.raise_for_status()
        data = response.json()["data"]
        text = ""
        for ayah in data["ayahs"]:
            text += f"{ayah['text']}\n\n"
        return text.strip()
    except Exception as e:
        logging.error(f"خطأ في جلب نص السورة: {e}")
        return None

def get_tafsir_automatic(surah_num):
    """
    جلب التفسير الميسر من مصدر موثوق (quranenc.com)
    هذا المصدر يقدم التفسير الصحيح لكل آية، وليس نص الآية
    """
    try:
        # استخدام API التفسير الميسر (وزارة الشؤون الإسلامية)
        url = f"https://quranenc.com/api/v1/translation/sura/arabic_moyassar/{surah_num}"
        response = requests.get(url, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            result = data.get("result", [])
            
            if not result:
                logging.warning(f"لا يوجد تفسير للسورة {surah_num}")
                return None

            # جلب اسم السورة
            surah_name = get_surah_info(surah_num)
            surah_name_text = surah_name["name"] if surah_name else str(surah_num)
            
            tafsir_text = f"📚 <b>تفسير سورة {surah_name_text}</b>\n"
            tafsir_text += "<b>التفسير الميسر</b>\n"
            tafsir_text += "━" * 25 + "\n\n"
            
            for item in result:
                ayah_num = item.get("ayah")
                # النص هنا هو التفسير الحقيقي وليس الآية
                explanation = item.get("translation", "").strip()
                
                if explanation:
                    tafsir_text += f"<b>الآية {ayah_num}:</b>\n"
                    tafsir_text += f"{explanation}\n\n"
            
            # التحقق من وجود محتوى فعلي
            if len(tafsir_text) > 200:
                return tafsir_text
            else:
                logging.warning(f"تفسير سورة {surah_num} قصير جداً")
                return None
            
    except Exception as e:
        logging.error(f"Error fetching tafsir for surah {surah_num}: {e}")
    
    return None

def send_quran_to_group(chat_id):
    """إرسال السورة والتفسير لمجموعة - رسالتين فقط"""
    global current_surah_index
    
    if current_surah_index >= len(SURAH_ORDER):
        current_surah_index = 0
        logging.info("🔄 تم الانتهاء من جميع السور، نبدأ من جديد")
    
    surah_num = SURAH_ORDER[current_surah_index]
    surah_info = get_surah_info(surah_num)
    
    if not surah_info:
        send_message(chat_id, f"❌ خطأ في جلب سورة {surah_num}")
        return
    
    logging.info(f"📖 جاري إرسال سورة {surah_info['name']}...")
    
    # ========== الرسالة الأولى: معلومات + نص السورة ==========
    header = f"""🌟 <b>سورة {surah_info['name']}</b>
━━━━━━━━━━━━━━━━━━━━━
📊 رقم السورة: {surah_info['order']}
📖 عدد الآيات: {surah_info['total_ayahs']}
📍 نوع السورة: {surah_info['revelation_type']}
━━━━━━━━━━━━━━━━━━━━━

<b>نص السورة:</b>\n\n"""
    
    surah_text = get_full_surah_text(surah_num)
    
    if surah_text:
        message1 = header + surah_text
        send_long_message(chat_id, message1)
        time.sleep(2)
    else:
        send_message(chat_id, header + "❌ لم يتوفر نص السورة")
        return
    
    # ========== الرسالة الثانية: التفسير الصحيح ==========
    tafsir = get_tafsir_automatic(surah_num)
    
    if tafsir:
        send_long_message(chat_id, tafsir)
        logging.info(f"✅ تم إرسال تفسير سورة {surah_info['name']}")
    else:
        # إذا فشل التفسير، نرسل رسالة توضيحية بدون روابط
        send_message(chat_id, f"📚 <b>تفسير سورة {surah_info['name']}</b>\n━━━━━━━━━━━━━━━━━━━━━\n\n⚠️ لم يتوفر التفسير حالياً. سيتم إضافته لاحقاً إن شاء الله.")
    
    # تحديث المؤشر للسورة القادمة
    current_surah_index += 1
    remaining = len(SURAH_ORDER) - current_surah_index
    logging.info(f"📊 السور المتبقية: {remaining}")

def send_quran_to_all_groups():
    """إرسال التفسير لجميع المجموعات"""
    for g in GROUPS:
        send_quran_to_group(g)
        time.sleep(3)

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
