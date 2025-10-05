
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
    # No app context needed for simple file writes
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
    with app.app_context():
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

@app.route('/api/accounts/add', methods=['POST'])
def add_account():
    phone = request.json['phone']
    if any(acc['phone'] == phone for acc in load_accounts()):
        return jsonify({"message": "Account already exists."}), 400
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    service = TelegramService(phone, API_ID, API_HASH, loop=loop)
    status, phone_code_hash = loop.run_until_complete(service.start_login())
    
    if status == 'CODE_SENT':
        pending_hashes[phone] = phone_code_hash
        response = {"message": "Verification code sent."}
    elif status == 'ALREADY_AUTHORIZED':
        user = loop.run_until_complete(service.get_me())
        accounts = load_accounts()
        new_account = {
            "phone": phone,
            "username": user.username if user else 'N/A',
            "settings": {"profile": {"first_name": user.first_name if user else '', "last_name": user.last_name if user else ''}}
        }
        accounts.append(new_account)
        save_accounts(accounts)
        response = {"message": "Account added successfully (already authorized)."}
    else:
        response = {"message": f"Could not log in: {status}"}

    loop.close()
    return jsonify(response)

@app.route('/api/accounts/finalize', methods=['POST'])
def finalize_account():
    data = request.json
    phone, code, password = data['phone'], data.get('code'), data.get('password')

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    service = TelegramService(phone, API_ID, API_HASH, loop=loop)

    if password:
        status = loop.run_until_complete(service.submit_password(password))
    elif code:
        phone_code_hash = pending_hashes.get(phone)
        if not phone_code_hash: 
            loop.close()
            return jsonify({"message": "Session expired, please try adding the account again."}), 400
        status = loop.run_until_complete(service.submit_code(code, phone_code_hash))
    else:
        loop.close()
        return jsonify({"message": "Code or password required."}), 400

    message = f"Login failed: {status}"
    if status == 'SUCCESS':
        if phone in pending_hashes: del pending_hashes[phone]
        user = loop.run_until_complete(service.get_me())
        accounts = load_accounts()
        if not any(a['phone'] == phone for a in accounts):
            new_account = {
                "phone": phone,
                "username": user.username if user else 'N/A',
                "settings": {"profile": {"first_name": user.first_name if user else '', "last_name": user.last_name if user else ''}}
            }
            accounts.append(new_account)
            save_accounts(accounts)
        message = "Account logged in and saved successfully."
    elif status == 'PASSWORD_NEEDED':
        message = "2FA password required."

    loop.close()
    return jsonify({"message": message})

@app.route('/api/accounts/delete', methods=['POST'])
def delete_account():
    phone = request.json['phone']
    save_accounts([acc for acc in load_accounts() if acc.get('phone') != phone])
    session_file = os.path.join(SESSIONS_DIR, phone.replace('+', '') + '.session')
    if os.path.exists(session_file): os.remove(session_file)
    return jsonify({"status": "ok", "message": "Account deleted."})

@app.route('/api/accounts/settings', methods=['POST'])
def save_account_settings():
    data = request.json
    phone, settings = data['phone'], data['settings']
    accounts = load_accounts()
    for acc in accounts:
        if acc['phone'] == phone:
            acc.setdefault('settings', {}).update(settings)
            break
    save_accounts(accounts)
    return jsonify({"status": "ok", "message": "Settings saved."})

@app.route('/api/accounts/profile', methods=['POST'])
def update_account_profile():
    data = request.json
    phone, profile_data = data['phone'], data['profile']
    account = get_account_by_phone(phone)
    if not account: return jsonify({"message": "Account not found"}), 404

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    service = TelegramService(phone, API_ID, API_HASH, loop=loop, proxy=account.get('settings', {}).get('proxy'))
    status = loop.run_until_complete(service.update_profile(**profile_data))
    loop.close()
    return jsonify({"message": status})

@app.route('/api/accounts/upload_avatar', methods=['POST'])
def upload_avatar():
    if 'avatar' not in request.files: return jsonify({"status": "error", "message": "No file part"}), 400
    file = request.files['avatar']
    if file.filename == '': return jsonify({"status": "error", "message": "No selected file"}), 400
    if file:
        filename = secure_filename(file.filename)
        unique_filename = str(uuid.uuid4()) + "_" + filename
        path = os.path.join(UPLOADS_DIR, unique_filename)
        file.save(path)
        return jsonify({"status": "ok", "path": path})

# --- API: Proxies ---
@app.route('/api/proxies')
def get_proxies():
    return jsonify(load_proxies())

@app.route('/api/proxies/add', methods=['POST'])
def add_proxy():
    proxy_data = request.json
    if not all(k in proxy_data for k in ['type', 'host', 'port']):
        return jsonify({"status": "error", "message": "Incomplete proxy data"}), 400
    proxies = load_proxies()
    proxy_data['id'] = str(uuid.uuid4())
    proxies.append(proxy_data)
    save_proxies(proxies)
    return jsonify({"status": "ok", "message": "Proxy added"})

@app.route('/api/proxies/delete', methods=['POST'])
def delete_proxy():
    proxy_id = request.json.get('id')
    save_proxies([p for p in load_proxies() if p.get('id') != proxy_id])
    return jsonify({"status": "ok", "message": "Proxy deleted"})

@app.route('/api/proxies/check', methods=['POST'])
def check_proxy():
    proxy = request.json
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    service = TelegramService("proxy_check", API_ID, API_HASH, proxy=proxy, loop=loop)
    is_working = loop.run_until_complete(service.check_proxy())
    loop.close()
    return jsonify({"status": "ok", "proxy_status": 'working' if is_working else 'not working'})

# --- API: Tags ---
@app.route('/api/tags')
def get_tags():
    return jsonify(load_tags())

@app.route('/api/tags/add', methods=['POST'])
def add_tag():
    tag_name = request.json.get('name').strip()
    if not tag_name: return jsonify({"status": "error", "message": "Tag name required"}), 400
    tags = load_tags()
    if tag_name not in tags: 
        tags.append(tag_name)
        save_tags(tags)
    return jsonify({"status": "ok", "message": "Tag added"})

@app.route('/api/tags/delete', methods=['POST'])
def delete_tag():
    tag_name = request.json.get('name')
    save_tags([t for t in load_tags() if t != tag_name])
    accounts = load_accounts()
    for acc in accounts:
        if 'tags' in acc.get('settings', {}) and tag_name in acc['settings']['tags']:
            acc['settings']['tags'].remove(tag_name)
    save_accounts(accounts)
    return jsonify({"status": "ok", "message": "Tag deleted"})

# --- API: Audiences ---
@app.route('/api/audiences/scrape', methods=['POST'])
def scrape_audience():
    data = request.json
    phone, chat_link = data.get('phone'), data.get('chat_link')
    account = get_account_by_phone(phone)
    if not account: return jsonify({"status": "error", "message": "Account not found"}), 404

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    service = TelegramService(phone, API_ID, API_HASH, loop=loop, **account.get('settings', {}))
    status, users = loop.run_until_complete(service.get_chat_participants(chat_link))
    loop.close()

    if status == 'SUCCESS':
        return jsonify({"status": "ok", "users": users})
    return jsonify({"status": "error", "message": status}), 500

@app.route('/api/audiences', methods=['GET'])
def list_audiences():
    if not os.path.exists(AUDIENCE_DIR): return jsonify([])
    return jsonify([f for f in os.listdir(AUDIENCE_DIR) if f.endswith('.json')])

@app.route('/api/audiences/save', methods=['POST'])
def save_audience():
    data = request.json
    name, users = data.get('name'), data.get('users')
    if not name or not users: return jsonify({"status": "error", "message": "Name and users required"}), 400

    filename = secure_filename(name) + '.json'
    save_json(os.path.join(AUDIENCE_DIR, filename), users)
    return jsonify({"status": "ok", "message": f"Audience '{name}' saved."})

@app.route('/api/audiences/<filename>', methods=['GET'])
def get_audience(filename):
    filepath = os.path.join(AUDIENCE_DIR, secure_filename(filename))
    if not os.path.exists(filepath): return jsonify({"status": "error", "message": "File not found"}), 404
    return jsonify(load_json(filepath))

@app.route('/api/audiences/delete', methods=['POST'])
def delete_audience():
    filename = request.json.get('filename')
    if not filename: return jsonify({"status": "error", "message": "Filename required"}), 400
    filepath = os.path.join(AUDIENCE_DIR, secure_filename(filename))
    if os.path.exists(filepath): os.remove(filepath)
    return jsonify({"status": "ok", "message": "Audience deleted."})

# --- API: Campaigns ---
@app.route('/api/campaigns', methods=['GET'])
def get_campaigns():
    return jsonify(load_campaigns())

@app.route('/api/campaigns/delete', methods=['POST'])
def delete_campaign():
    campaign_id = request.json.get('id')
    save_campaigns([c for c in load_campaigns() if c.get('id') != campaign_id])
    if campaign_id in active_campaign_threads: del active_campaign_threads[campaign_id]
    return jsonify({"status": "ok", "message": "Campaign deleted"})

@app.route('/api/campaigns/start', methods=['POST'])
def start_campaign_route():
    data = request.json
    name, audience_file, account_phones, message = data.get('name'), data.get('audience_file'), data.get('account_phones'), data.get('message')
    if not all([name, audience_file, account_phones, message]):
        return jsonify({"status": "error", "message": "All fields are required"}), 400

    audience_path = os.path.join(AUDIENCE_DIR, secure_filename(audience_file))
    if not os.path.exists(audience_path): return jsonify({"status": "error", "message": "Audience file not found"}), 404
    
    users_to_message = load_json(audience_path)
    new_campaign = {
        "id": str(uuid.uuid4()), "name": name, "audience_file": audience_file,
        "total_users": len(users_to_message), "progress": 0, "status": "Starting",
        "created_at": datetime.datetime.utcnow().isoformat()
    }
    
    campaigns = load_campaigns()
    campaigns.insert(0, new_campaign)
    save_campaigns(campaigns)

    thread = threading.Thread(target=run_campaign_thread, args=(app, new_campaign, users_to_message, account_phones, message))
    thread.daemon = True
    thread.start()
    active_campaign_threads[new_campaign['id']] = thread

    return jsonify({"status": "ok", "message": "Campaign started", "campaign": new_campaign})

def run_campaign_thread(flask_app, campaign, users, account_phones, message):
    with flask_app.app_context():
        campaign_id = campaign['id']
        update_campaign_status(campaign_id, "Running", f"0/{len(users)}")
        logging.info(f"[Campaign:{campaign_id}] Starting...")

        # This part needs a better distribution and progress tracking mechanism
        # For now, let's just process them sequentially for simplicity
        sent_count = 0
        for i, user in enumerate(users):
            if campaign_id not in active_campaign_threads: break
            
            phone_to_use = account_phones[i % len(account_phones)]
            account = get_account_by_phone(phone_to_use)
            if not account: continue

            # This creates a new loop for every message, which is inefficient
            # A better design would be a worker pool or a single loop per account worker
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            service = TelegramService(phone_to_use, API_ID, API_HASH, loop=loop, **account.get('settings', {}))
            
            try:
                status = loop.run_until_complete(service.send_message(user.get('id'), message))
                if status == "SUCCESS": sent_count += 1
                else: logging.error(f"[Campaign:{campaign_id}] Failed to send to {user.get('id')}: {status}")
            except Exception as e:
                logging.error(f"[Campaign:{campaign_id}] Exception sending to {user.get('id')}: {e}")
            finally:
                loop.close()
            
            update_campaign_status(campaign_id, "Running", f"{i + 1}/{len(users)}")
            time.sleep(random.randint(5, 15))

        final_status = "Completed" if sent_count == len(users) else "Finished with errors"
        update_campaign_status(campaign_id, final_status, f"{sent_count}/{len(users)}")
        logging.info(f"[Campaign:{campaign_id}] {final_status}.")
        if campaign_id in active_campaign_threads: del active_campaign_threads[campaign_id]


# --- Main Execution ---
if __name__ == '__main__':
    setup_directories()
    app.run(debug=True, threaded=True, use_reloader=False)
