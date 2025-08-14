# Import necessary libraries
import logging
import json
import os
import re
from flask import Flask, request, jsonify
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
from google.oauth2 import service_account
from googleapiclient.discovery import build

# --- Configuration and Setup ---

# Your bot's token and admin username from Render environment variables
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_USERNAME = 'sureshotquestion'

# Google Drive API credentials
GOOGLE_DRIVE_API_KEY_FILE = '/etc/secrets/service-account.json'

# A dictionary to store Google Drive links for different courses
DRIVE_LINKS = {
    "pcm": "1-vabXx9a0qu5M8MwVtKYq1UFSW_FF5Pe",
    "physics": "1OVjZFvLTroUiHRY4naSkN-pfJsifv913",
    "maths": "1LCCFMCYUDXj81CWf3t5qZv9rVuUcGz2i",
    "chemistry": "1eEtJdYEBpsDoS0gZvPQOmUTBCL6qjM-A",
    "bio": "1eq2ZDabtXYGQjOhW1UYwTNTCFCWg3mFB"
}

# A dictionary to persistently store user states (e.g., what they want to buy)
USER_STATES_FILE = 'user_states.json'
user_states = {}

def load_user_states():
    global user_states
    try:
        with open(USER_STATES_FILE, 'r') as f:
            data = json.load(f)
            user_states = {int(k): v for k, v in data.items()}
            logging.info(f"Loaded {len(user_states)} user states from file.")
    except (FileNotFoundError, json.JSONDecodeError):
        logging.warning("No user states file found. Starting with an empty dictionary.")

def save_user_states():
    with open(USER_STATES_FILE, 'w') as f:
        json.dump({str(k): v for k, v in user_states.items()}, f)
        logging.info("Saved user states to file.")

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- Google Drive API Integration ---
def grant_drive_access(email, folder_id):
    """Grants a user access to a specific Google Drive folder."""
    credentials = service_account.Credentials.from_service_account_file(
        GOOGLE_DRIVE_API_KEY_FILE,
        scopes=['https://www.googleapis.com/auth/drive']
    )
    drive_service = build('drive', 'v3', credentials=credentials)
    
    permission = {
        'type': 'user',
        'role': 'reader',
        'emailAddress': email
    }
    
    try:
        drive_service.permissions().create(
            fileId=folder_id,
            body=permission,
            fields='id',
            sendNotificationEmail=False
        ).execute()
        logging.info(f"Granted access to {email} for folder {folder_id}.")
        return True
    except Exception as e:
        logging.error(f"Failed to grant access: {e}")
        return False

# --- Telegram Handlers ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = (
        fr"Hello there, {update.effective_user.first_name}\! Welcome to Arvind Academy\'s Sure Shot Questions bot\."
        "\n\n"
        fr"I\'m here to help you with information about our educational courses\."
        "\n\n"
        r"You can ask me about our courses by typing one of the following:"
        "\n"
        r"\- `buy <subject>` \- to start a purchase"
        "\n"
        r"\- `price` \- See all pricing details"
        "\n"
        r"\- `pcm` \- Get details about the PCM combo"
        "\n"
        r"\- `bio` \- Get details about the Biology course"
        "\n\n"
        r"Here\'s a quick look at what we offer:"
    )
    # IMPORTANT: You must replace this placeholder URL with the actual public URL of your image.
    promo_image_url = "poster.jpg"
    
    try:
        await update.message.reply_text(welcome_message, parse_mode=ParseMode.MARKDOWN_V2)
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=promo_image_url)
    except Exception as e:
        logging.error(f"Failed to send start message: {e}")
        await update.message.reply_text(r"Sorry, I couldn\'t send the welcome message\. This might be because the image URL is invalid\.", parse_mode=ParseMode.MARKDOWN_V2)

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    user_message = update.message.text.lower().strip()
    
    # Check for specific keywords
    if user_message.startswith("buy"):
        parts = user_message.split()
        if len(parts) > 1:
            subject = parts[1]
            if subject in DRIVE_LINKS:
                user_states[user_id] = {'course': subject, 'status': 'awaiting_payment'}
                save_user_states()

                price = "250₹" if subject == "pcm" else "100₹"
                payment_text = (
                    fr"To purchase the {subject.upper()} course for {price}, please complete the payment and then send me your email address for Google Drive access\."
                )
                await update.message.reply_text(payment_text, parse_mode=ParseMode.MARKDOWN_V2)
            else:
                await update.message.reply_text(fr"Sorry, I don\'t have a course for \'{subject}\'\. Please choose from PCM, Physics, Maths, Chemistry, or Bio\.", parse_mode=ParseMode.MARKDOWN_V2)
        else:
            await update.message.reply_text(r"Please specify a course you want to buy, for example: `buy pcm`\.", parse_mode=ParseMode.MARKDOWN_V2)
    elif user_message in ["price", "cost", "how much"]:
        promotional_text = (
            "Arvind Academy\'s 🔥Sure Shot Questions🔥LATEST 2025 🔥\n\n"
            "ALL WITH \[ HD PDF \] SOLUTIONS\n\n"
            "🔥PCM Combo: 250₹\n\n"
            "🔥Single Subject: 100₹\n\n"
            "🔥 BIO \(EXCLUSIVE\) \- 100₹"
        )
        await update.message.reply_text(promotional_text, parse_mode=ParseMode.MARKDOWN_V2)
    elif user_id in user_states and user_states[user_id].get('status') == 'awaiting_email':
        email = update.message.text.strip()
        if re.match(r"[^@]+@[^@]+\.[^@]+", email):
            user_states[user_id]['email'] = email
            user_states[user_id]['status'] = 'payment_requested'
            save_user_states()
            await update.message.reply_text(fr"Thank you, {update.effective_user.first_name}\! Your email address \'{email}\' has been recorded\. I will grant you access after payment is verified\.", parse_mode=ParseMode.MARKDOWN_V2)
        else:
            await update.message.reply_text(r"That doesn\'t look like a valid email address\. Please try again\.", parse_mode=ParseMode.MARKDOWN_V2)
    else:
        await start_command(update, context)

# --- Flask Webhook Handler ---
app = Flask(__name__)
application = ApplicationBuilder().token(BOT_TOKEN).build()

# Register Telegram handlers
application.add_handler(CommandHandler('start', start_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))

@app.route('/' + BOT_TOKEN, methods=['POST'])
async def webhook_handler():
    # This route receives updates from Telegram
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.process_update(update)
    return jsonify({'status': 'ok'})

@app.route('/payment_webhook', methods=['POST'])
def handle_payment_webhook():
    # This endpoint receives webhooks from a payment gateway like Razorpay or Stripe
    data = request.json
    logging.info(f"Received payment webhook: {data}")
    
    # IMPORTANT: Implement webhook signature verification here for security.
    
    if data.get('event') == 'payment.completed':
        user_email = data['payload']['payment']['entity']['email']
        course_name = data['payload']['payment']['entity']['notes']['course']
        user_chat_id = data['payload']['payment']['entity']['notes']['chat_id']
        
        folder_id = DRIVE_LINKS.get(course_name)
        
        if folder_id and grant_drive_access(user_email, folder_id):
            message = fr"Congratulations\! Your payment for the {course_name.upper()} course has been verified\. You now have access to the Google Drive folder\."
            application.bot.send_message(chat_id=user_chat_id, text=message, parse_mode=ParseMode.MARKDOWN_V2)
            return jsonify({'status': 'success'}), 200
    
    return jsonify({'status': 'not handled'}), 200

# --- Main Bot Functionality ---
if __name__ == '__main__':
    load_user_states()
    application.run_polling()
