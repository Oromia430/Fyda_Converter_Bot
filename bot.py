import io
import os
import re
import telebot
from telebot import types
from PIL import Image, ImageOps, ImageDraw, ImageFont
import pytesseract
from flask import Flask
import threading

# CONFIGURATION
API_TOKEN = '8974775722:AAEdkBUxx02cwzLLzGT6Fa5hqSWtveqGz6A'  
ADMIN_CHAT_ID = 'YOUR_PERSONAL_TELEGRAM_ID_HERE'  # Chat ID kee kan Elias

bot = telebot.TeleBot(API_TOKEN)

user_lang = {}             
user_balances = {}         
user_pending_payments = {}

MY_TELEBIRR = "TeleBirr (Elias Fikadu) • 0913701367"
MY_CBE = "CBE (Elias Fikadu) • 1000270143788"

# Fonni maamilootaa kaardicha irratti barreeffamuuf (Render irratti default kan ta'e)
try:
    font_regular = ImageFont.load_default()
    font_bold = ImageFont.load_default()
except:
    font_regular = None

MESSAGES = {
    'en': {
        'send_id': "📥 Please send the screenshot of the <b>Fayda ID</b> (both sides together).",
        'processing': "⚙️ Reading text and recreating original ID... Please wait.",
        'no_credit': "⚠️ You don't have enough credits! Type /topup to buy."
    },
    'am': {
        'send_id': "📥 እባክዎ የመታወቂያውን ፎቶ (ሁለቱንም ገጽ በአንድ ላይ የያዘውን) ይላኩ።",
        'processing': "⚙️ መታወቂያው ላይ ያለውን ፅሁፍ እያነበብኩ ነው... እባክዎ ይጠብቁ።",
        'no_credit': "⚠️ በቂ ክሬዲት የለዎትም! ለመግዛት /topup ይፃፉ።"
    },
    'om': {
        'send_id': "📥 Maaloo suuraa screenshot <b>Fayda ID</b> (Fuula duraa fi duubaa wal bira jiru) ergaa.",
        'processing': "⚙️ Barruu kaardichaa dubbisaafi ijaarbaa jira... Maaloo obsaan eegaa.",
        'no_credit': "⚠️ Kireditii gahaa hin qabdhan! Guuttachuuf /topup jedhaa."
    }
}

@bot.message_handler(commands=['start', 'language'])
def start_bot(message):
    user_id = message.from_user.id
    if user_id not in user_balances:
        user_balances[user_id] = 2  # Kireditii 2 bilisaan
        
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("English 🇬🇧", callback_data="lang_en"),
        types.InlineKeyboardButton("አማርኛ 🇪🇹", callback_data="lang_am"),
        types.InlineKeyboardButton("Afaan Oromoo 🌳", callback_data="lang_om")
    )
    bot.send_message(message.chat.id, "🌐 Choose / Filadhaa / ይምረጡ:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def handle_lang_selection(call):
    user_id = call.from_user.id
    lang = call.data.split('_')[1]
    user_lang[user_id] = lang
    bot.send_message(call.message.chat.id, MESSAGES[lang]['send_id'], parse_mode='HTML')

# --- CREDIT CONTROLLER (Manual Admin Approval) ---
@bot.message_handler(commands=['topup'])
def topup_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("7 credits — 200 ETB", callback_data="pkg_7_200"),
        types.InlineKeyboardButton("18 credits — 500 ETB", callback_data="pkg_18_500")
    )
    bot.send_message(message.chat.id, "📦 Package filadhaa:", reply_markup=markup)

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
    msg = bot.send_message(call.message.chat.id, f"💵 Maaloo <b>{pending['price']} ETB</b> gara herrega kanaan ergaa:\n• {method}\n\nErga kaffaltanii booda <b>Transaction ID</b> barreessaa.", parse_mode='HTML')
    bot.register_next_step_handler(msg, send_to_admin_verification)

def send_to_admin_verification(message):
    user_id = message.from_user.id
    tx_id = message.text.strip()
    pending = user_pending_payments.get(user_id)
    if not pending: return
    
    bot.send_message(message.chat.id, "⏳ <b>Transaction ID keessan mirkanaawaa jira... Admin yeroo gabaabaa keessatti siif fe'a.</b>", parse_mode='HTML')
    
    admin_markup = types.InlineKeyboardMarkup()
    admin_markup.add(types.InlineKeyboardButton("Mirkaneessi ✅", callback_data=f"approve_{user_id}_{pending['credits']}"))
    bot.send_message(ADMIN_CHAT_ID, f"🔔 <b>Kafaltii Haaraa:</b>\n\n• User ID: <code>{user_id}</code>\n• Tx ID: <code>{tx_id}</code>\n• Kireditii: {pending['credits']}", reply_markup=admin_markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_'))
def admin_approve(call):
    _, user_id, credits = call.data.split('_')
    user_id, credits = int(user_id), int(credits)
    user_balances[user_id] = user_balances.get(user_id, 0) + credits
    bot.edit_message_text(f"✅ User {user_id} tiif Kireditii {credits} kennameera.", call.message.chat.id, call.message.message_id)
    bot.send_message(user_id, f"🎉 <b>Kafaltiin keessan mirkanaayeera! Kireditiin {credits} dabalameera.</b>", parse_mode='HTML')

# --- CORE PROCESSING: TEXT EXTRACTION & ORIGINAL LAYOUT ---
@bot.message_handler(content_types=['photo'])
def process_fayda_id(message):
    user_id = message.from_user.id
    lang = user_lang.get(user_id, 'om')
    
    if user_balances.get(user_id, 0) <= 0:
        bot.send_message(message.chat.id, MESSAGES[lang]['no_credit'], parse_mode='HTML')
        return

    bot.send_message(message.chat.id, MESSAGES[lang]['processing'], parse_mode='HTML')
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        full_img = Image.open(io.BytesIO(downloaded_file))
        
        W, H = full_img.size
        
        # 1. Split Screenshot Into Front and Back
        back_side = full_img.crop((0, 0, int(W * 0.5), int(H * 0.5)))
        front_side = full_img.crop((int(W * 0.5), 0, W, int(H * 0.5)))
        
        # 2. OCR - Text Dubbisuu (English fi Amharic)
        ocr_text = pytesseract.image_to_string(front_side, lang='eng+amh')
        
        # Data sassaabuu (Regex fayyadamanii)
        fin_match = re.search(r'FIN\s*[:\s]*(\d+)', ocr_text)
        fin_number = fin_match.group(1) if fin_match else "3051 8063 5013"
        
        # 3. Crop User Photo From Screenshot
        # Suuraa namaa qorree baasna (Coordinates standard kaardichaa irraa)
        fw, fh = front_side.size
        user_photo = front_side.crop((int(fw * 0.7), int(fh * 0.2), int(fw * 0.95), int(fh * 0.7)))
        
        # 4. Templates keenya banuu
        card_w, card_h = 1011, 638
        try:
            front_tmpl = Image.open('t1_template.jpg').convert('RGB').resize((card_w, card_h))
            back_tmpl = Image.open('back_template.jpg').convert('RGB').resize((card_w, card_h))
        except:
            # Yoo templatiin dhabame blank ijaara
            front_tmpl = Image.new('RGB', (card_w, card_h), '#E6F4EA')
            back_tmpl = Image.new('RGB', (card_w, card_h), '#E6F4EA')

        # Suuraa namaa template haaraa irratti past gochuu
        user_photo_resized = user_photo.resize((230, 290))
        front_tmpl.paste(user_photo_resized, (720, 140))
        
        # Barruu dubbisame template haaraa irratti barreesuu
        draw = ImageDraw.Draw(front_tmpl)
        draw.text((80, 480), f"FIN {fin_number}", fill="#000000", font=font_bold)
        
        # 5. Mirroring & Canvas Construction
        front_final = ImageOps.mirror(front_tmpl)
        back_final = ImageOps.mirror(back_tmpl)
        
        canvas = Image.new('RGB', (2480, 3508), '#FFFFFF')
        canvas.paste(back_final, (150, 200))      # Gala Dugdaa (Bitaa)
        canvas.paste(front_final, (1250, 200))    # Fuula Duraa (Mirga)
        
        bio = io.BytesIO()
        canvas.save(bio, 'JPEG', quality=100)
        bio.seek(0)
        
        user_balances[user_id] -= 1
        bot.send_photo(message.chat.id, bio, caption="✅ <b>ID Original Bifa Kanaan Qophaayeera!</b>\n🪞 Mirror: <b>ON (Ready for PVC Print)</b>", parse_mode='HTML')
        
    except Exception as e:
        bot.reply_to(message, f"❌ Dogoggorri uumameera: {str(e)}")

app = Flask('')
@app.route('/')
def home(): return "Active"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

if __name__ == "__main__":
    t = threading.Thread(target=run_flask)
    t.start()
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
