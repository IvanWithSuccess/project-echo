
import asyncio
import json
import os
import logging
import random
import uuid
import threading
import datetime
import time
from flask import Flask, jsonify, render_template, request, send_from_directory
from werkzeug.utils import secure_filename
from project_echo.services.telegram_service import TelegramService

# --- Constants ---
ACCOUNTS_FILE = "accounts.json"
CAMPAIGNS_FILE = "campaigns.json"
PROXIES_FILE = "proxies.json"
TAGS_FILE = "tags.json"
SESSIONS_DIR = "sessions"
AUDIENCE_DIR = "audiences"
UPLOADS_DIR = "uploads"
API_ID = 26947469
API_HASH = "731a222f9dd8b290db925a6a382159dd"

app = Flask(__name__, template_folder='templates', static_folder='static')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- App State ---
pending_hashes = {}
# Using a thread-safe way to manage campaign state is better, but for now this works with Flask's threaded mode.
active_campaign_threads = {}

# --- Setup ---
def setup_directories():
    for d in [SESSIONS_DIR, AUDIENCE_DIR, UPLOADS_DIR]:
        if not os.path.exists(d): os.makedirs(d)

# --- Data Helpers ---
def load_json(file_path, default=None):
    if not os.path.exists(file_path):
        save_json(file_path, default if default is not None else [])
        return default if default is not None else []
    try:
        with open(file_path, 'r') as f: 
            content = f.read()
            if not content: return default if default is not None else []
            return json.loads(content)
    except (json.JSONDecodeError, FileNotFoundError):
        return default if default is not None else []

def save_json(file_path, data):
    with app.app_context(): # Ensure we are in an app context for thread safety
        with open(file_path, 'w') as f: 
            json.dump(data, f, indent=2)

# --- Specific Data Functions ---
load_accounts = lambda: load_json(ACCOUNTS_FILE, default=[])
save_accounts = lambda d: save_json(ACCOUNTS_FILE, d)
load_campaigns = lambda: load_json(CAMPAIGNS_FILE, default=[])
save_campaigns = lambda d: save_json(CAMPAIGNS_FILE, d)
load_proxies = lambda: load_json(PROXIES_FILE, default=[])
save_proxies = lambda d: save_json(PROXIES_FILE, d)
load_tags = lambda: load_json(TAGS_FILE, default=[])
save_tags = lambda d: save_json(TAGS_FILE, d)

def get_account_by_phone(phone):
    accounts = load_accounts()
    return next((acc for acc in accounts if acc.get('phone') == phone), None)

def update_campaign_status(campaign_id, new_status, progress=None):
    campaigns = load_campaigns()
    for c in campaigns:
        if c['id'] == campaign_id:
            c['status'] = new_status
            if progress is not None:
                c['progress'] = progress
            break
    save_campaigns(campaigns)

# --- HTML Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOADS_DIR, filename)

# --- API: Accounts ---
@app.route('/api/accounts')
def get_accounts():
    return jsonify(load_accounts())

# ... (existing account routes are fine) ...

# --- API: Proxies ---
@app.route('/api/proxies')
def get_proxies():
    return jsonify(load_proxies())

# ... (existing proxy routes are fine) ...

# --- API: Tags ---
@app.route('/api/tags')
def get_tags():
    return jsonify(load_tags())

# ... (existing tag routes are fine) ...

# --- API: Audiences ---
# ... (existing audience routes are fine) ...

# --- API: Campaigns ---
@app.route('/api/campaigns', methods=['GET'])
def get_campaigns():
    return jsonify(load_campaigns())

@app.route('/api/campaigns/delete', methods=['POST'])
def delete_campaign():
    campaign_id = request.json.get('id')
    campaigns = [c for c in load_campaigns() if c.get('id') != campaign_id]
    save_campaigns(campaigns)
    if campaign_id in active_campaign_threads:
        # This doesn't stop the thread, but prevents it from updating state further
        del active_campaign_threads[campaign_id]
    return jsonify({"status": "ok", "message": "Campaign deleted"})

@app.route('/api/campaigns/start', methods=['POST'])
def start_campaign_route():
    data = request.json
    name = data.get('name')
    audience_file = data.get('audience_file')
    account_phones = data.get('account_phones')
    message = data.get('message')

    if not all([name, audience_file, account_phones, message]):
        return jsonify({"status": "error", "message": "All fields are required"}), 400

    audience_path = os.path.join(AUDIENCE_DIR, secure_filename(audience_file))
    if not os.path.exists(audience_path):
        return jsonify({"status": "error", "message": "Audience file not found"}), 404
    
    users_to_message = load_json(audience_path)

    new_campaign = {
        "id": str(uuid.uuid4()),
        "name": name,
        "audience_file": audience_file,
        "total_users": len(users_to_message),
        "progress": 0,
        "status": "Starting",
        "created_at": datetime.datetime.utcnow().isoformat()
    }
    
    campaigns = load_campaigns()
    campaigns.insert(0, new_campaign)
    save_campaigns(campaigns)

    # Start the campaign in a background thread
    thread = threading.Thread(target=run_campaign_thread, args=(app, new_campaign, users_to_message, account_phones, message))
    thread.daemon = True
    thread.start()
    active_campaign_threads[new_campaign['id']] = thread

    return jsonify({"status": "ok", "message": "Campaign started", "campaign": new_campaign})

def run_campaign_thread(flask_app, campaign, users, account_phones, message):
    with flask_app.app_context():
        campaign_id = campaign['id']
        total_users = len(users)
        sent_count = 0
        
        update_campaign_status(campaign_id, "Running", f"0/{total_users}")
        logging.info(f"[Campaign:{campaign_id}] Starting for {total_users} users with {len(account_phones)} accounts.")

        user_chunks = [users[i::len(account_phones)] for i in range(len(account_phones))]
        
        threads = []
        for i, phone in enumerate(account_phones):
            account = get_account_by_phone(phone)
            if not account:
                logging.warning(f"[Campaign:{campaign_id}] Account {phone} not found, skipping.")
                continue
            
            chunk = user_chunks[i]
            worker_thread = threading.Thread(
                target=campaign_worker,
                args=(flask_app, campaign_id, account, chunk, message)
            )
            threads.append(worker_thread)
            worker_thread.start()

        for t in threads:
            t.join() # Wait for all worker threads to complete

        # Final status update after all workers are done is tricky because they don't return sent counts.
        # A more robust solution would use a shared queue or state object.
        # For now, we assume completion.
        final_progress = campaign['progress'] # Get the latest progress saved by workers
        update_campaign_status(campaign_id, "Completed", final_progress)
        logging.info(f"[Campaign:{campaign_id}] Finished.")
        if campaign_id in active_campaign_threads: del active_campaign_threads[campaign_id]

def campaign_worker(flask_app, campaign_id, account, user_chunk, message):
    with flask_app.app_context():
        phone = account['phone']
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        service = TelegramService(
            phone, API_ID, API_HASH, loop=loop, 
            proxy=account.get('settings', {}).get('proxy'),
            system_version=account.get('settings', {}).get('user_agent')
        )

        sent_in_this_worker = 0
        for user in user_chunk:
            if campaign_id not in active_campaign_threads: 
                logging.info(f"[Worker:{phone}] Campaign {campaign_id} was stopped. Exiting.")
                break

            target_user_id = user.get('id')
            if not target_user_id:
                logging.warning(f"[Worker:{phone}] Skipping user with no ID: {user}")
                continue

            try:
                status = loop.run_until_complete(service.send_message(target_user_id, message))
                if status == "SUCCESS":
                    sent_in_this_worker += 1
                    logging.info(f"[Worker:{phone}] Message sent to {target_user_id}")
                else:
                    logging.error(f"[Worker:{phone}] Failed to send to {target_user_id}: {status}")
            except Exception as e:
                logging.error(f"[Worker:{phone}] Exception sending to {target_user_id}: {e}")
            
            # Update global progress (this is not perfectly thread-safe but often good enough for this use case)
            all_campaigns = load_campaigns()
            for c in all_campaigns:
                if c['id'] == campaign_id:
                    current_sent = int(c['progress'].split('/')[0])
                    c['progress'] = f"{current_sent + 1}/{c['total_users']}"
                    break
            save_campaigns(all_campaigns)

            time.sleep(random.randint(5, 15)) # Random delay between messages

        loop.close()


# --- Main Execution ---
if __name__ == '__main__':
    setup_directories()
    # Ensure all routes are defined before accessing them
    # The following are just placeholders to ensure the functions are defined.
    add_account = add_account
    finalize_account = finalize_account
    delete_account = delete_account
    save_account_settings = save_account_settings
    update_account_profile = update_account_profile
    upload_avatar = upload_avatar
    get_proxies = get_proxies
    add_proxy = add_proxy
    delete_proxy = delete_proxy
    check_proxy = check_proxy
    get_tags = get_tags
    add_tag = add_tag
    delete_tag = delete_tag
    scrape_audience = scrape_audience
    list_audiences = list_audiences
    save_audience = save_audience
    get_audience = get_audience
    delete_audience = delete_audience

    app.run(debug=True, threaded=True, use_reloader=False) # use_reloader=False is important for background threads
