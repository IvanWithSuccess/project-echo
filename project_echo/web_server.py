
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
API_ID = 26947469
API_HASH = "731a222f9dd8b290db925a6a382159dd"

app = Flask(__name__, template_folder='templates', static_folder='static')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- App State ---
pending_hashes = {}
active_campaigns = set()

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

load_accounts = lambda: load_json(ACCOUNTS_FILE)
save_accounts = lambda d: save_json(ACCOUNTS_FILE, d)
load_campaigns = lambda: load_json(CAMPAIGNS_FILE)
save_campaigns = lambda d: save_json(CAMPAIGNS_FILE, d)

def save_account(phone, username):
    accounts = load_accounts()
    if not any(acc['phone'] == phone for acc in accounts):
        accounts.append({"phone": phone, "username": username})
        save_accounts(accounts)

# --- Graceful Shutdown for Async tasks ---
async def graceful_shutdown(loop):
    tasks = [t for t in asyncio.all_tasks(loop) if t is not asyncio.current_task(loop)]
    if tasks:
        for task in tasks: task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

# --- API: Accounts ---
@app.route('/api/accounts')
def get_accounts():
    return jsonify(load_accounts())

@app.route('/api/accounts/add', methods=['POST'])
def add_account():
    phone = request.json.get('phone')
    if not phone: return jsonify({'status': 'error', 'message': 'Phone number required.'}), 400

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    service = TelegramService(phone, API_ID, API_HASH)
    
    status, result = loop.run_until_complete(service.start_login())
    
    response = {}
    if status == 'CODE_SENT':
        pending_hashes[phone] = result  # phone_code_hash
        response = {'status': 'ok', 'message': 'Verification code sent.'}
    elif status == 'ALREADY_AUTHORIZED':
        user = loop.run_until_complete(service.get_me())
        save_account(phone, user.username if user else None)
        response = {'status': 'ok', 'message': 'Account already authorized and added.'}
    else:
        response = {'status': 'error', 'message': f'Failed to start login process: {result}'}

    loop.run_until_complete(graceful_shutdown(loop))
    loop.close()
    
    return jsonify(response)

@app.route('/api/accounts/finalize', methods=['POST'])
def finalize_account():
    phone = request.json.get('phone')
    code = request.json.get('code')
    password = request.json.get('password')
    phone_code_hash = pending_hashes.get(phone)

    if not phone: return jsonify({'status': 'error', 'message': 'Phone number is missing.'}), 400

    # FIX: Create and set event loop *before* initializing TelegramService
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    service = TelegramService(phone, API_ID, API_HASH)

    status = ""
    if code and phone_code_hash:
        status = loop.run_until_complete(service.submit_code(code, phone_code_hash))
    elif password:
        status = loop.run_until_complete(service.submit_password(password))

    response = {}
    if status == 'SUCCESS':
        user = loop.run_until_complete(service.get_me())
        save_account(phone, user.username if user else None)
        if phone in pending_hashes: del pending_hashes[phone]
        response = {'status': 'ok', 'message': 'Account connected successfully!'}
    elif status == 'PASSWORD_NEEDED':
        response = {'status': 'ok', 'message': '2FA password required.'}
    else:
        response = {'status': 'error', 'message': f'Failed to finalize connection: {status}'}
    
    loop.run_until_complete(graceful_shutdown(loop))
    loop.close()

    return jsonify(response)

@app.route('/api/accounts/delete', methods=['POST'])
def delete_account_route():
    phone_to_delete = request.json.get('phone')
    accounts = load_accounts()
    new_accounts = [acc for acc in accounts if acc.get('phone') != phone_to_delete]
    save_accounts(new_accounts)
    
    session_file = os.path.join(SESSIONS_DIR, f"{phone_to_delete.replace('+', '')}.session")
    if os.path.exists(session_file):
        os.remove(session_file)
        
    return jsonify({'status': 'ok', 'message': 'Account deleted successfully.'})

# --- API: Audiences ---
@app.route('/api/audience/scrape', methods=['POST'])
def scrape_audience_route():
    phone = request.json.get('phone')
    chat_link = request.json.get('chat_link')
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    service = TelegramService(phone, API_ID, API_HASH)
    
    status, users = loop.run_until_complete(service.get_chat_participants(chat_link))

    loop.run_until_complete(graceful_shutdown(loop))
    loop.close()

    if status == 'SUCCESS':
        return jsonify({'status': 'ok', 'users': users})
    else:
        return jsonify({'status': 'error', 'message': status}), 500

@app.route('/api/audiences/save', methods=['POST'])
def save_audience_route():
    filename = request.json.get('filename')
    users = request.json.get('users')
    
    if not filename or not users:
        return jsonify({'status': 'error', 'message': 'Filename and users are required.'}), 400
        
    safe_filename = "".join(c for c in filename if c.isalnum() or c in ('_', '-')) + '.json'
    file_path = os.path.join(AUDIENCE_DIR, safe_filename)
    
    save_json(file_path, users)
    return jsonify({'status': 'ok', 'message': f'Audience saved to {safe_filename}'})

@app.route('/api/audiences')
def get_audiences_route():
    try:
        files = [f for f in os.listdir(AUDIENCE_DIR) if f.endswith('.json')]
        return jsonify({'status': 'ok', 'audiences': files})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# --- API: Campaigns ---
@app.route('/api/campaigns')
def get_campaigns():
    return jsonify(load_campaigns())

@app.route('/api/campaigns/save', methods=['POST'])
def save_campaign_route():
    data = request.json
    campaign_id = data.get('id')
    campaigns = load_campaigns()
    
    if campaign_id:
        campaign = next((c for c in campaigns if c.get('id') == campaign_id), None)
        if campaign:
            campaign.update(data)
        else:
            return jsonify({'status': 'error', 'message': 'Campaign not found'}), 404
    else:
        data['id'] = str(uuid.uuid4())
        data['status'] = 'Draft'
        campaigns.append(data)
        
    save_campaigns(campaigns)
    return jsonify({'status': 'ok', 'message': 'Campaign saved successfully!', 'campaigns': campaigns})

def run_campaign_in_new_loop(campaign_id):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_campaign_async(campaign_id))
    loop.close()

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

    campaign['status'] = 'In Progress'
    save_json(CAMPAIGNS_FILE, campaigns)

    try:
        audience_file = os.path.join(AUDIENCE_DIR, campaign['audience'])
        users = load_json(audience_file)
        accounts = campaign['accounts']
        message = campaign['message']

        if not users or not accounts:
            raise ValueError("Audience or accounts are empty for this campaign.")

        account_cycle = 0
        for i, user in enumerate(users):
            phone = accounts[account_cycle]
            user_id = user.get('id')
            
            logging.info(f"[Campaign:{campaign_id}] -> ({i+1}/{len(users)}) to user ID {user_id} via {phone}")
            
            service = TelegramService(phone, API_ID, API_HASH)
            status = await service.send_message(user_id, message)

            if status != "SUCCESS":
                logging.warning(f"[Campaign:{campaign_id}] Failed to send to {user_id}: {status}")

            account_cycle = (account_cycle + 1) % len(accounts)
            delay = random.randint(30, 60)
            logging.info(f"[Campaign:{campaign_id}] Waiting for {delay} seconds...")
            await asyncio.sleep(delay)
        
        campaign['status'] = 'Completed'
        logging.info(f"Campaign {campaign_id} completed successfully.")

    except Exception as e:
        logging.error(f"Campaign {campaign_id} failed: {e}")
        campaign['status'] = 'Failed'
    finally:
        campaigns = load_json(CAMPAIGNS_FILE)
        final_campaign_state = next((c for c in campaigns if c.get('id') == campaign_id), None)
        if final_campaign_state:
            final_campaign_state['status'] = campaign['status']
            save_json(CAMPAIGNS_FILE, campaigns)
        active_campaigns.remove(campaign_id)

@app.route('/api/campaigns/start', methods=['POST'])
def start_campaign_route():
    campaign_id = request.json.get('id')
    if not campaign_id:
        return jsonify({'status': 'error', 'message': 'Campaign ID is required.'}), 400
    
    campaign_thread = threading.Thread(target=run_campaign_in_new_loop, args=(campaign_id,), daemon=True)
    campaign_thread.start()

    return jsonify({'status': 'ok', 'message': 'Campaign started. Check server logs for progress.'})

# --- Web Page Route ---
@app.route('/')
def index():
    return render_template('index.html')
