import io
import os
import re
import telebot
from telebot import types
from PIL import Image, ImageOps
import requests
from flask import Flask
import threading

# API TOKENS (Token bot keetii fi Id kee as galchi)
API_TOKEN = '8974775722:AAEdkBUxx02cwzLLzGT6Fa5hqSWtveqGz6A'  
ADMIN_CHAT_ID = 123456789  # Elias Telegram Chat ID (Lakkoofsa qofa godhi)

bot = telebot.TeleBot(API_TOKEN)

user_lang = {}             
user_balances = {}         

MESSAGES = {
    'en': {
        'send_id': "📥 Please send the **Fayda ID** image or screenshot.",
        'processing': "⚙️ Reading FIN/FAN and creating original Layout... Please wait.",
        'no_credit': "⚠️ You don't have enough credits! Please contact the admin to recharge."
    },
    'am': {
        'send_id': "📥 እባክዎ የመታወቂያውን ፎቶ ወይም ስክሪንሹት ይላኩ።",
        'processing': "⚙️ የ FIN/FAN ቁጥር እያነበብኩና መታወቂያውን እያዘጋጀሁ ነው... ይጠብቁ።",
        'no_credit': "⚠️ በቂ ክሬዲት የለዎትም! ለመግዛት እባክዎ አስተዳዳሪውን ያነጋግሩ።"
    },
    'om': {
        'send_id': "📥 Maaloo suuraa ykn screenshot **Fayda ID** keessanii ergaa.",
        'processing': "⚙️ Lakkoofsa FIN/FAN dubbisee kaardii keessan original ijaarbaa jira... Maaloo obsaan eegaa.",
        'no_credit': "⚠️ Kireditii gahaa hin qabdhan! Maaloo kireditii guuttachuuf Admin dubbisaa."
    }
}

@bot.message_handler(commands=['start', 'language'])
def start_bot(message):
    user_id = message.from_user.id
    if user_id not in user_balances:
        user_balances[user_id] = 2  # Gift 2 credits for free testing
        
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("English 🇬🇧", callback_data="lang_en"),
        types.InlineKeyboardButton("አማርኛ 🇪🇹", callback_data="lang_am"),
        types.InlineKeyboardButton("Afaan Oromoo 🌳", callback_data="lang_om")
    )
    bot.send_message(message.chat.id, "🌐 Choose Language / Filadhaa / ይምረጡ:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def handle_lang_selection(call):
    user_id = call.from_user.id
    lang = call.data.split('_')[1]
    user_lang[user_id] = lang
    bot.send_message(call.message.id, MESSAGES[lang]['send_id'], parse_mode='Markdown')

# ==================== TO'ANNOO KAFFALTII OFII KEETIIN (ADMIN ADD CREDIT) ====================
# Ati dhuunfaatti maamila irraa erga kaffaltii fuutee booda Command kanaan kireditii fedaaf:
# Fakkeenya: /add 12345678 18  (Kun user suniif kireditii 18 kenna)
@bot.message_handler(commands=['add'])
def add_credit_manual(message):
    if message.from_user.id != ADMIN_CHAT_ID:
        return
    try:
        parts = message.text.split()
        target_user = int(parts[1])
        credits_to_add = int(parts[2])
        
        user_balances[target_user] = user_balances.get(target_user, 0) + credits_to_add
        bot.reply_to(message, f"✅ User `{target_user}` tiif kireditii {credits_to_add} feeteetta!", parse_mode='Markdown')
        
        # Maamilaaf ergaa mirkanaa'uu fi kireditii isaa haaraa itti himu gachuu
        bot.send_message(target_user, f"🎉 **Kafaltiin keessan mirkanaayeera! Kireditiin {credits_to_add} herrega keessanitti dabalameera.**\n• Kireditii hundi: {user_balances[target_user]}")
    except Exception as e:
        bot.reply_to(message, "❌ Dogoggora fayyadamaa! Haala kanaan barreessi: `/add UserID Kireditii`", parse_mode='Markdown')

# ==================== ONLINE OCR ENGINE ====================
def extract_text_online(image_bytes):
    try:
        url = "https://api.ocr.space/parse/image"
        payload = {"apikey": "helloworld", "language": "eng"}
        files = {"file": ("image.jpg", image_bytes, "image/jpeg")}
        response = requests.post(url, data=payload, files=files).json()
        text = response['ParsedResults'][0]['ParsedText']
        return text
    except:
        return ""

# ==================== CORE ID PROCESSING ====================
@bot.message_handler(content_types=['photo'])
def process_fayda_image(message):
    user_id = message.from_user.id
    lang = user_lang.get(user_id, 'om')
    
    if user_balances.get(user_id, 0) <= 0:
        bot.send_message(message.chat.id, MESSAGES[lang]['no_credit'], parse_mode='Markdown')
        return

    bot.send_message(message.chat.id, MESSAGES[lang]['processing'], parse_mode='Markdown')
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        ocr_text = extract_text_online(downloaded_file)
        fin_match = re.search(r'(FIN|FAN)\s*[:\s]*([\d\s]+)', ocr_text, re.IGNORECASE)
        detected_id = fin_match.group(2).strip() if fin_match else "Unknown"
        
        full_img = Image.open(io.BytesIO(downloaded_file))
        W, H = full_img.size
        
        if W > H:
            front_side = full_img.crop((0, 0, int(W * 0.5), H))
            back_side = full_img.crop((int(W * 0.5), 0, W, H))
        else:
            front_side = full_img
            back_side = full_img
        
        card_w, card_h = 1011, 638
        front_final = front_side.resize((card_w, card_h), Image.Resampling.LANCZOS)
        back_final = back_side.resize((card_w, card_h), Image.Resampling.LANCZOS)
        
        front_final = ImageOps.mirror(front_final)
        back_final = ImageOps.mirror(back_final)
        
        canvas = Image.new('RGB', (2480, 3508), '#FFFFFF')
        canvas.paste(back_final, (150, 200))      
        canvas.paste(front_final, (1250, 200))    
        
        bio = io.BytesIO()
        canvas.save(bio, 'JPEG', quality=100)
        bio.seek(0)
        
        user_balances[user_id] -= 1
        
        caption_msg = f"✅ **Fayda ID Processed Successfully!**\n• Detected ID: `{detected_id}`\n• Credit Left: {user_balances[user_id]}\n\n🪞 Mirror Layout: **ON (Ready for PVC Print)**"
        bot.send_photo(message.chat.id, bio, caption=caption_msg, parse_mode='Markdown')
        
    except Exception as e:
        bot.reply_to(message, f"❌ Dogoggora: {str(e)}")

app = Flask('')
@app.route('/')
def home(): return "Active"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

if __name__ == "__main__":
    t = threading.Thread(target=run_flask)
    t.start()
    bot.infinity_polling(timeout=15, long_polling_timeout=10)
