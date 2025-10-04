
import asyncio
import json
import os
import logging
import random
import uuid
import threading
from flask import Flask, jsonify, render_template, request
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
active_campaigns = set()

# --- Setup ---
def setup_directories():
    for d in [SESSIONS_DIR, AUDIENCE_DIR, UPLOADS_DIR]:
        if not os.path.exists(d): os.makedirs(d)

# --- Data Helpers ---
def load_json(file_path, default=None):
    if not os.path.exists(file_path):
        # Create the file with default content if it doesn't exist
        save_json(file_path, default if default is not None else [])
        return default if default is not None else []
    try:
        with open(file_path, 'r') as f: 
            # Handle empty file case
            content = f.read()
            if not content: return default if default is not None else []
            return json.loads(content)
    except (json.JSONDecodeError, FileNotFoundError):
        return default if default is not None else []

def save_json(file_path, data):
    with open(file_path, 'w') as f: json.dump(data, f, indent=2)

# --- Specific Data Functions (Defined Before Use) ---
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

# --- HTML Routes ---
@app.route('/')
def index():
    return render_template('index.html')

# --- API: Accounts ---
@app.route('/api/accounts')
def get_accounts():
    return jsonify(load_accounts())

@app.route('/api/accounts/add', methods=['POST'])
def add_account():
    phone = request.json['phone']
    accounts = load_accounts()
    if any(acc['phone'] == phone for acc in accounts):
        return jsonify({"message": "Account already exists."}), 400
    
    service = TelegramService(phone, API_ID, API_HASH)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    status, phone_code_hash = loop.run_until_complete(service.start_login())
    loop.close()
    
    if status == 'CODE_SENT':
        pending_hashes[phone] = phone_code_hash
        return jsonify({"message": "Verification code sent."})
    elif status == 'ALREADY_AUTHORIZED':
        # This part requires a running loop to get user, so we create it again
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        user = loop.run_until_complete(service.get_me())
        loop.close()
        new_account = {
            "phone": phone,
            "username": user.username if user else 'N/A',
            "settings": {"profile": {"first_name": user.first_name if user else '', "last_name": user.last_name if user else ''}}
        }
        accounts.append(new_account)
        save_accounts(accounts)
        return jsonify({"message": "Account added successfully (already authorized)."}), 201
    elif 'PASSWORD_NEEDED' in status:
        return jsonify({"message": "2FA password required."})
    else:
        return jsonify({"message": f"Error: {status}"}), 500

@app.route('/api/accounts/finalize', methods=['POST'])
def finalize_account():
    data = request.json
    phone = data['phone']
    code = data.get('code')
    password = data.get('password')
    phone_code_hash = pending_hashes.get(phone)

    service = TelegramService(phone, API_ID, API_HASH)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    if password:
        status = loop.run_until_complete(service.submit_password(password))
    elif code and phone_code_hash:
        status = loop.run_until_complete(service.submit_code(code, phone_code_hash))
    else:
        loop.close()
        return jsonify({"message": "Code or password required."}), 400

    if status == 'SUCCESS':
        if phone in pending_hashes: del pending_hashes[phone]
        user = loop.run_until_complete(service.get_me())
        accounts = load_accounts()
        new_account = {
            "phone": phone,
            "username": user.username if user else 'N/A',
            "settings": {"profile": {"first_name": user.first_name if user else '', "last_name": user.last_name if user else ''}}
        }
        if not any(a['phone'] == phone for a in accounts):
            accounts.append(new_account)
        save_accounts(accounts)
        message = "Account logged in and saved successfully."
    elif status == 'PASSWORD_NEEDED':
        message = "2FA password required."
    else:
        message = f"Login failed: {status}"
    
    loop.close()
    return jsonify({"message": message})

@app.route('/api/accounts/delete', methods=['POST'])
def delete_account():
    phone = request.json['phone']
    accounts = [acc for acc in load_accounts() if acc.get('phone') != phone]
    save_accounts(accounts)
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
            # Merge settings to not lose keys
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

    service = TelegramService(phone, API_ID, API_HASH, proxy=account.get('settings', {}).get('proxy'))
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    status = loop.run_until_complete(service.update_profile(
        first_name=profile_data.get('first_name'),
        last_name=profile_data.get('last_name'),
        bio=profile_data.get('bio'),
        avatar_path=profile_data.get('avatar_path')
    ))
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
    proxies = [p for p in load_proxies() if p.get('id') != proxy_id]
    save_proxies(proxies)
    return jsonify({"status": "ok", "message": "Proxy deleted"})

@app.route('/api/proxies/check', methods=['POST'])
def check_proxy():
    proxy = request.json
    service = TelegramService(phone="proxy_check", api_id=API_ID, api_hash=API_HASH, proxy=proxy)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    is_working = loop.run_until_complete(service.check_proxy())
    loop.close()
    status = 'working' if is_working else 'not working'
    return jsonify({"status": "ok", "proxy_status": status})

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
    tags = [t for t in load_tags() if t != tag_name]
    save_tags(tags)
    return jsonify({"status": "ok", "message": "Tag deleted"})


# --- Main Execution ---
if __name__ == '__main__':
    setup_directories()
    app.run(debug=True)
