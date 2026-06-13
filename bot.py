import io
import os
import re
import telebot
from telebot import types
from PIL import Image, ImageOps
import requests
from flask import Flask
import threading

# API TOKENS (Id kee fi token bot keetii as galchi)
API_TOKEN = '8974775722:AAEdkBUxx02cwzLLzGT6Fa5hqSWtveqGz6A'  
ADMIN_CHAT_ID = 'YOUR_PERSONAL_TELEGRAM_ID_HERE'  # Elias Telegram Chat ID

bot = telebot.TeleBot(API_TOKEN)

user_lang = {}             
user_balances = {}         
user_pending_payments = {}

MY_TELEBIRR = "TeleBirr (Elias Fikadu) • 0913701367"
MY_CBE = "CBE (Elias Fikadu) • 1000270143788"

MESSAGES = {
    'en': {
        'send_id': "📥 Please send the **Fayda ID** image or screenshot.",
        'processing': "⚙️ Reading FIN/FAN and creating original Layout... Please wait.",
        'no_credit': "⚠️ You don't have enough credits! Type /topup to buy."
    },
    'am': {
        'send_id': "📥 እባክዎ የመታወቂያውን ፎቶ ወይም ስክሪንሹት ይላኩ።",
        'processing': "⚙️ የ FIN/FAN ቁጥር እያነበብኩና መታወቂያውን እያዘጋጀሁ ነው... ይጠብቁ።",
        'no_credit': "⚠️ በቂ ክሬዲት የለዎትም! ለመግዛት /topup ይፃፉ።"
    },
    'om': {
        'send_id': "📥 Maaloo suuraa ykn screenshot **Fayda ID** keessanii ergaa.",
        'processing': "⚙️ Lakkoofsa FIN/FAN dubbisee kaardii keessan original ijaarbaa jira... Maaloo obsaan eegaa.",
        'no_credit': "⚠️ Kireditii gahaa hin qabdhan! Guuttachuuf /topup jedhaa."
    }
}

@bot.message_handler(commands=['start', 'language'])
def start_bot(message):
    user_id = message.from_user.id
    if user_id not in user_balances:
        user_balances[user_id] = 2  # Gift 2
        
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
    bot.send_message(call.message.chat.id, MESSAGES[lang]['send_id'], parse_mode='Markdown')

# ==================== TO'ANNOO KAFALTII (ADMIN VERIFICATION) ====================
@bot.message_handler(commands=['topup'])
def topup_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("7 credits — 200 ETB", callback_data="pkg_7_200"),
        types.InlineKeyboardButton("18 credits — 500 ETB", callback_data="pkg_18_500")
    )
    bot.send_message(message.chat.id, "📦 Package Kireditii filadhaa:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('pkg_'))
def pack_select(call):
    user_id = call.from_user.id
    _, credits, price = call.data.split('_')
    user_pending_payments[user_id] = {'credits': int(credits), 'price': int(price)}
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton(MY_TELEBIRR, callback_data="pay_tele"),
        types.InlineKeyboardButton(MY_CBE, callback_data="pay_cbe")
    )
    bot.send_message(call.message.chat.id, f"🏦 Kafaltii {price} ETB raawwachuuf herrega filadhaa:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('pay_'))
def bank_select(call):
    user_id = call.from_user.id
    pending = user_pending_payments.get(user_id)
    if not pending: return
    method = MY_TELEBIRR if call.data == "pay_tele" else MY_CBE
    msg = bot.send_message(call.message.chat.id, f"💵 Maaloo **{pending['price']} ETB** herrega kanaan ergaa:\n• {method}\n\nErga kaffaltanii booda **Transaction ID** qofa barreessaa nuuf ergaa.", parse_mode='Markdown')
    bot.register_next_step_handler(msg, send_to_admin_verification)

def send_to_admin_verification(message):
    user_id = message.from_user.id
    tx_id = message.text.strip()
    pending = user_pending_payments.get(user_id)
    if not pending: return
    
    bot.send_message(message.chat.id, "⏳ **Transaction ID keessan mirkanaawaa jira... Admin yeroo gabaabaa keessatti cheek godhee siif fe'a.**", parse_mode='Markdown')
    
    admin_markup = types.InlineKeyboardMarkup()
    admin_markup.add(
        types.InlineKeyboardButton("Verify ✅ (Kireditii Ergi)", callback_data=f"approve_{user_id}_{pending['credits']}"),
        types.InlineKeyboardButton("Reject ❌ (Kufisi)", callback_data=f"reject_{user_id}")
    )
    bot.send_message(ADMIN_CHAT_ID, f"🔔 **Kafaltii Haaraa dhufe (Cheek Godhi):**\n\n• Maqaa: {message.from_user.first_name}\n• User ID: `{user_id}`\n• Tx ID: `{tx_id}`\n• Kireditii: {pending['credits']} ({pending['price']} ETB)", reply_markup=admin_markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_'))
def admin_approve(call):
    _, user_id, credits = call.data.split('_')
    user_id, credits = int(user_id), int(credits)
    
    user_balances[user_id] = user_balances.get(user_id, 0) + credits
    bot.edit_message_text(f"✅ User {user_id} tiif Kireditii {credits} feeteetta. Herregni kee mirkanaa'eera.", call.message.chat.id, call.message.message_id)
    bot.send_message(user_id, f"🎉 **Kafaltiin keessan Elias'n mirkanaayeera! Kireditiin {credits} dabalameera.** Amma ID keessan erguu dandeessu.", parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_'))
def admin_reject(call):
    user_id = int(call.data.split('_')[1])
    bot.edit_message_text(f"❌ Kafaltii User {user_id} kufisteetta (Rejected).", call.message.chat.id, call.message.message_id)
    bot.send_message(user_id, "❌ **Kafaltiin keessan herrega irratti hin argamne. Maaloo Transaction ID sirrii ta'uu cheek godhaatii deebisaa yaala.**", parse_mode='Markdown')

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
