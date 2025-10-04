
import asyncio
import json
import os
import logging
import random
import uuid
import threading
from flask import Flask, jsonify, render_template, request
from project_echo.services.telegram_service import TelegramService

# --- Constants ---
ACCOUNTS_FILE = "accounts.json"
CAMPAIGNS_FILE = "campaigns.json"
SESSIONS_DIR = "sessions"
AUDIENCE_DIR = "audiences"
UPLOADS_DIR = "uploads" # Added
API_ID = 26947469
API_HASH = "731a222f9dd8b290db925a6a382159dd"

app = Flask(__name__, template_folder='templates', static_folder='static')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- App State ---
pending_hashes = {}
active_campaigns = set()

# --- Setup ---
def setup_directories():
    for d in [SESSIONS_DIR, AUDIENCE_DIR, UPLOADS_DIR]: # Added UPLOADS_DIR
        if not os.path.exists(d): os.makedirs(d)

# --- Data Helpers ---
def load_json(file_path, default=None):
    if not os.path.exists(file_path): return default if default is not None else []
    try:
        with open(file_path, 'r') as f: return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError): return default if default is not None else []

def save_json(file_path, data):
    with open(file_path, 'w') as f: json.dump(data, f, indent=2)

load_accounts = lambda: load_json(ACCOUNTS_FILE)
save_accounts = lambda d: save_json(ACCOUNTS_FILE, d)
# ... (other helpers are unchanged)

def get_account_by_phone(phone):
    accounts = load_accounts()
    return next((acc for acc in accounts if acc.get('phone') == phone), None)


def save_account(phone, username):
    accounts = load_accounts()
    if not any(acc.get('phone') == phone for acc in accounts):
        new_account = {
            "phone": phone, "username": username,
            "settings": {
                "tags": [], "system_version": None,
                "proxy": None, "profile": {}
            }
        }
        accounts.append(new_account)
        save_accounts(accounts)

# --- API: Accounts ---

def _get_service_for_phone(phone):
    acc = get_account_by_phone(phone)
    if not acc: return None
    settings = acc.get('settings', {})
    return TelegramService(phone, API_ID, API_HASH, 
                             system_version=settings.get('system_version'),
                             proxy=settings.get('proxy'))

@app.route('/api/accounts')
def get_accounts():
    return jsonify(load_accounts())

@app.route('/api/accounts/add', methods=['POST'])
def add_account():
    phone = request.json.get('phone')
    service = TelegramService(phone, API_ID, API_HASH) # No settings on first add
    # ... (rest of the function is unchanged)

@app.route('/api/accounts/finalize', methods=['POST'])
def finalize_account():
    phone = request.json.get('phone')
    service = TelegramService(phone, API_ID, API_HASH) # No settings on finalize
    # ... (rest of the function is unchanged)

@app.route('/api/accounts/profile', methods=['POST'])
def update_account_profile():
    data = request.json
    phone = data.get('phone')
    profile_data = data.get('profile', {})

    service = _get_service_for_phone(phone)
    if not service:
        return jsonify({'status': 'error', 'message': 'Account not found.'}), 404

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    result_message = loop.run_until_complete(service.update_profile(
        first_name=profile_data.get('first_name'),
        last_name=profile_data.get('last_name'),
        bio=profile_data.get('bio'),
        avatar_path=profile_data.get('avatar_path')
    ))

    loop.close()
    
    if "successful" in result_message:
        return jsonify({'status': 'ok', 'message': result_message})
    else:
        return jsonify({'status': 'error', 'message': result_message}), 500


# ... (the rest of the file like audience/campaign routes use _get_service_for_phone)
# --- API: Audiences ---
@app.route('/api/audience/scrape', methods=['POST'])
def scrape_audience_route():
    phone = request.json.get('phone')
    chat_link = request.json.get('chat_link')
    
    service = _get_service_for_phone(phone)
    if not service:
        return jsonify({'status': 'error', 'message': 'Account not found.'}), 404

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    status, users = loop.run_until_complete(service.get_chat_participants(chat_link))
    loop.close()
    # ... (rest is unchanged)

# --- API: Campaigns ---
async def run_campaign_async(campaign_id):
    # ...
    # Inside the loop for sending messages
    service = _get_service_for_phone(phone) # Get service with settings for each account
    if not service:
        logging.warning(f"[Campaign:{campaign_id}] Could not find settings for {phone}, skipping.")
        continue
    
    status = await service.send_message(user_id, message)
    # ...

@app.route('/')
def index():
    setup_directories() # Ensure directories exist on startup
    return render_template('index.html')

