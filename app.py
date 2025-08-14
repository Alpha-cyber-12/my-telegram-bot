# Import necessary libraries
import logging
import os
from flask import Flask, request, jsonify
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import asyncio
from asgiref.wsgi import WsgiToAsgi

# --- Configuration and Setup ---

# Your bot's token from Render environment variables
BOT_TOKEN = os.environ.get('BOT_TOKEN')

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- Telegram Handlers ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! The webhook is working correctly.")

# --- Flask Webhook Handler ---
app = Flask(__name__)
# The Application object needs to be created globally for the webhook to work correctly
application = ApplicationBuilder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler('start', start_command))

@app.route('/' + BOT_TOKEN, methods=['POST'])
async def webhook_handler():
    # This route receives updates from Telegram
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.process_update(update)
    return jsonify({'status': 'ok'})

# --- Main Bot Functionality ---
if __name__ == '__main__':
    # This part is not executed on Render, but it's good practice for local testing
    print("Bot is ready to receive webhooks.")

# Expose the Flask app to Gunicorn
# This is how Gunicorn finds the app
asgi_app = WsgiToAsgi(app)
