# --- Bot Telegram Auto Reply Canggih Versi AI Ringan ---
# Versi: 28 April 2025

import logging
import os
import time
import requests
import csv
import io
import random
import pytz
from datetime import datetime
from rapidfuzz import fuzz
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CallbackContext

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- Link CSV Google Sheet ---
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSKd5gh5iOzsGtoFglkdqZ6WDah1dbYWYffNvRolpdvSF-UJ9EEB2HaT7EYSqv0l_k2wrlJRhpivOyO/pub?output=csv"

# --- Token Telegram ---
TELEGRAM_TOKEN = "8136574407:AAHIvRwJSGDvkfGS-rtmJYeHMk08AqfwjiA"

# --- User Session Memory ---
user_session = {}  # {user_id: (session_active:bool, last_active_time:int, last_topic:str)}

# --- Jawapan Random Bila Tak Jumpa ---
unknown_replies = [
    "Maaf, saya tak pasti maksud awak... cuba tanya lain?",
    "Hmm... saya tak faham sangat. Boleh ulang soalan?",
    "Saya tengah fikir jawapan... boleh tanya dengan ayat lain?",
    "Hehe... saya blur kejap. Cuba explain lagi."
    "..."
]

# --- Ambil Data dari Google Sheet ---
def get_sheet_data():
    try:
        response = requests.get(CSV_URL)
        response.raise_for_status()
        content = response.content.decode('utf-8')
        reader = csv.DictReader(io.StringIO(content))
        return list(reader)
    except Exception as e:
        logging.error(f"Failed to fetch sheet data: {str(e)}")
        return []

# --- Normalize Text ---
def preprocess(text):
    text = (text or '').lower().strip()
    text = text.replace('tak', 'tidak').replace('x', 'tidak')  # Normalisasi kecil
    return text

# --- Tentukan Perlu Balas atau Tidak ---
def should_reply(update):
    user_id = update.message.from_user.id
    text = preprocess(update.message.text)
    current_time = time.time()

    if user_id in user_session:
        session_active, last_active, last_topic = user_session[user_id]
        if current_time - last_active > 300:
            user_session[user_id] = (False, current_time, None)
            session_active = False
    else:
        session_active = False

    if session_active:
        if any(stop in text for stop in ["bye", "stop", "end"]):
            user_session[user_id] = (False, current_time, None)
            return False
        user_session[user_id] = (True, current_time, user_session[user_id][2])
        return True

    if any(greet in text for greet in ["admin", "assalamualaikum", "salam", "aleeya", "selamat pagi", "hi", "hello"]):
        user_session[user_id] = (True, current_time, None)
        return True

    if update.message.sticker or ("👍" in (update.message.text or "")):
        user_session[user_id] = (True, current_time, None)
        return True

    return False

# --- Bila Terima Mesej ---
async def handle_message(update: Update, context: CallbackContext):
    try:
        if not should_reply(update):
            return

        text = preprocess(update.message.text)
        logging.info(f"[DEBUG] Incoming Message: {text}")

        records = get_sheet_data()
        best_score = 0
        best_reply = None

        for record in records:
            keyword = preprocess(record.get('Keyword'))
            jawapan = (record.get('Jawapan') or '').strip()

            if keyword:
                score = fuzz.partial_ratio(keyword, text)
                if score > best_score:
                    best_score = score
                    best_reply = jawapan

        if best_score >= 75 and best_reply:
            # Auto detect jawapan khas
            if best_reply.startswith("http"):
                await update.message.reply_photo(best_reply)
            elif best_reply.lower() == "is.time":
                malaysia_time = datetime.now(pytz.timezone('Asia/Kuala_Lumpur')).strftime("%H:%M:%S")
                await update.message.reply_text(f"Sekarang jam {malaysia_time}")
            elif best_reply.lower().startswith("is.image:"):
                filename = best_reply.split(":",1)[1].strip()
                with open(filename, "rb") as photo:
                    await update.message.reply_photo(photo)
            else:
                await update.message.reply_text(best_reply)
            # Simpan last topic user
            user_session[update.message.from_user.id] = (True, time.time(), text)
        else:
            await update.message.reply_text(random.choice(unknown_replies))

    except Exception as e:
        logging.error(f"[ERROR] {str(e)}")
        await update.message.reply_text("Maaf... server tengah sibuk. Cuba lagi sekejap ya 🙏")

# --- Main Function ---
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, handle_message))
    print("🤖 Bot AI Lite sudah jalan...")
    app.run_polling()

# --- Mula Run ---
if __name__ == '__main__':
    main()
