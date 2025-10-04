
import asyncio
import json
import os
import logging
import random
import time
import uuid
from flask import Flask, jsonify, render_template, request
from project_echo.services.telegram_service import TelegramService

# --- Constants ---
ACCOUNTS_FILE = "accounts.json"
CAMPAIGNS_FILE = "campaigns.json"
SESSIONS_DIR = "sessions"
AUDIENCE_DIR = "audiences"
API_ID = 26947469
API_HASH = "731a222f9dd8b290db925a6a382159dd"

app = Flask(__name__, template_folder='templates', static_folder='static')
logging.basicConfig(level=logging.INFO)

# --- App State ---
pending_hashes = {}
active_campaigns = set() # Track running campaign IDs

# --- Setup ---
def setup_directories():
    for d in [SESSIONS_DIR, AUDIENCE_DIR]:
        if not os.path.exists(d): os.makedirs(d)

# --- Data Helpers ---
def load_json(file_path, default=None):
    if not os.path.exists(file_path): return default if default is not None else []
    try:
        with open(file_path, 'r') as f: return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError): return default if default is not None else []

def save_json(file_path, data):
    with open(file_path, 'w') as f: json.dump(data, f, indent=2)

# --- Main Background Task ---
async def run_campaign_async(campaign_id):
    if campaign_id in active_campaigns:
        logging.warning(f"Campaign {campaign_id} is already running.")
        return

    active_campaigns.add(campaign_id)
    logging.info(f"Starting campaign {campaign_id}...")

    campaigns = load_json(CAMPAIGNS_FILE)
    campaign = next((c for c in campaigns if c.get('id') == campaign_id), None)
    if not campaign: 
        logging.error(f"Campaign {campaign_id} not found.")
        active_campaigns.remove(campaign_id)
        return

    # Update status to In Progress
    campaign['status'] = 'In Progress'
    save_json(CAMPAIGNS_FILE, campaigns)

    try:
        audience_file = os.path.join(AUDIENCE_DIR, campaign['audience'])
        users = load_json(audience_file)
        accounts = campaign['accounts']
        message = campaign['message']

        if not users or not accounts:
            raise ValueError("Audience or accounts are empty.")

        account_cycle = 0
        for i, user in enumerate(users):
            phone = accounts[account_cycle]
            user_id = user.get('id')
            
            logging.info(f"[Campaign:{campaign_id}] Sending to user {i+1}/{len(users)} (ID: {user_id}) using {phone}")
            
            service = TelegramService(phone, API_ID, API_HASH)
            status = await service.send_message(user_id, message)

            if status != "SUCCESS":
                logging.warning(f"[Campaign:{campaign_id}] Failed to send to {user_id}: {status}")

            # Cycle to the next account
            account_cycle = (account_cycle + 1) % len(accounts)

            # Smart delay
            delay = random.randint(30, 60)
            logging.info(f"[Campaign:{campaign_id}] Waiting for {delay} seconds...")
            await asyncio.sleep(delay)
        
        campaign['status'] = 'Completed'
        logging.info(f"Campaign {campaign_id} completed successfully.")

    except Exception as e:
        logging.error(f"Campaign {campaign_id} failed: {e}")
        campaign['status'] = 'Failed'
    finally:
        save_json(CAMPAIGNS_FILE, campaigns)
        active_campaigns.remove(campaign_id)


# --- API Routes ---
@app.route('/api/campaigns/start', methods=['POST'])
def start_campaign_route():
    campaign_id = request.json.get('id')
    if not campaign_id: return jsonify({'status': 'error', 'message': 'Campaign ID is required.'}), 400
    
    # Run the campaign in a background thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    # Using a thread to not block the Flask server
    asyncio.run_coroutine_threadsafe(run_campaign_async(campaign_id), loop)
    # A better way for modern python > 3.9 would be asyncio.to_thread
    # For simplicity and compatibility, this approach is fine for now.

    return jsonify({'status': 'ok', 'message': 'Campaign started in the background.'})


# --- (Other routes like /api/accounts, /api/audiences remain the same) ---
# ... Previous API routes from web_server.py go here ...
# --- Web Page Routes ---

@app.route('/')
def index():
    return render_template('index.html')

# --- Main Entry Point ---
if __name__ == '__main__':
    setup_directories()
    app.run(debug=True, port=5000)
