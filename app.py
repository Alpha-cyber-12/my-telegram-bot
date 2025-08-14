# A new structure using a web framework (like Flask) to handle webhooks.
# This requires a new set of libraries and a different deployment model.
import logging
from flask import Flask, request
from telegram import Bot
from google.oauth2 import service_account
from googleapiclient.discovery import build

# --- Configuration and Setup ---

# Your bot's token
BOT_TOKEN = '8381956118:AAHkItv_4WZId44p8DwIzLe5SMsXhX5l94Y'

# Initialize a Telegram Bot instance
bot = Bot(token=BOT_TOKEN)

# Google Drive API credentials (from your JSON key file)
GOOGLE_DRIVE_API_KEY_FILE = 'path/to/your/service-account.json'

# A dictionary to store Google Drive links for different courses
DRIVE_LINKS = {
    "pcm": "1-vabXx9a0qu5M8MwVtKYq1UFSW_FF5Pe", # Note: These are now folder IDs, not full links
    "physics": "1OVjZFvLTroUiHRY4naSkN-pfJsifv913",
    # ... other courses
}

# --- Google Drive API Integration ---
def grant_drive_access(email, folder_id):
    """Grants a user access to a specific Google Drive folder."""
    credentials = service_account.Credentials.from_service_account_file(
        GOOGLE_DRIVE_API_KEY_FILE,
        scopes=['https://www.googleapis.com/auth/drive']
    )
    drive_service = build('drive', 'v3', credentials=credentials)
    
    # Create the permission
    permission = {
        'type': 'user',
        'role': 'reader',  # 'reader' for view-only, 'writer' for editing
        'emailAddress': email
    }
    
    try:
        drive_service.permissions().create(
            fileId=folder_id,
            body=permission,
            fields='id',
            sendNotificationEmail=False # Set to True to send an email notification
        ).execute()
        logging.info(f"Granted access to {email} for folder {folder_id}.")
        return True
    except Exception as e:
        logging.error(f"Failed to grant access: {e}")
        return False

# --- Webhook Handler (using Flask) ---
app = Flask(__name__)

@app.route('/webhook/payment-success', methods=['POST'])
def handle_payment_webhook():
    """Endpoint for the payment gateway to send payment success notifications."""
    data = request.json
    
    # IMPORTANT: You must implement code here to verify the webhook signature
    # for security. This depends on your payment gateway (Stripe, Razorpay, etc.).

    if data.get('event') == 'payment.succeeded':
        user_email = data['payload']['email']
        course_name = data['payload']['metadata']['course']
        user_chat_id = data['payload']['metadata']['chat_id']
        
        folder_id = DRIVE_LINKS.get(course_name)
        
        if folder_id and grant_drive_access(user_email, folder_id):
            message = f"Congratulations! Your payment for the {course_name.upper()} course has been verified. You now have access to the Google Drive folder."
            # Await is not used here as this is a synchronous Flask route.
            # You would need an async Flask (like Quart) or a background task
            # to handle this gracefully in a real application.
            bot.send_message(chat_id=user_chat_id, text=message)
            return 'OK', 200
    
    return 'Event not handled', 200

# This is a very simplified example. The full implementation would require
# a more robust architecture, error handling, and security measures.
