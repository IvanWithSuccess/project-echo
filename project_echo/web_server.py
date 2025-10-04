
import asyncio
import json
import os
import logging
from flask import Flask, jsonify, render_template, request
from project_echo.services.telegram_service import TelegramService

# --- Constants ---
ACCOUNTS_FILE = "accounts.json"
SESSIONS_DIR = "sessions"
API_ID = 26947469
API_HASH = "731a222f9dd8b290db925a6a382159dd"

app = Flask(
    __name__,
    template_folder='templates',
    static_folder='static'
)

# --- State Management ---
pending_hashes = {}

# --- Helper Functions ---

def load_accounts():
    if not os.path.exists(ACCOUNTS_FILE):
        return []
    try:
        with open(ACCOUNTS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def save_accounts(accounts):
    with open(ACCOUNTS_FILE, 'w') as f:
        json.dump(accounts, f, indent=2)

def save_account(phone, username):
    accounts = load_accounts()
    if not any(acc['phone'] == phone for acc in accounts):
        accounts.append({"phone": phone, "username": username})
        save_accounts(accounts)

async def graceful_shutdown(loop):
    """Cancels all running tasks and shuts down the loop."""
    tasks = [t for t in asyncio.all_tasks(loop=loop) if t is not asyncio.current_task(loop=loop)]
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)

# --- API Routes ---

@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    return jsonify(load_accounts())

@app.route('/api/accounts/add', methods=['POST'])
def add_account():
    phone = request.json.get('phone')
    if not phone:
        return jsonify({'status': 'error', 'message': 'Phone number is required.'}), 400

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    service = TelegramService(phone, API_ID, API_HASH)
    status, phone_code_hash = loop.run_until_complete(service.start_login())
    loop.run_until_complete(graceful_shutdown(loop))
    loop.close()

    if status == 'CODE_SENT':
        pending_hashes[phone] = phone_code_hash
        return jsonify({'status': 'ok', 'message': 'Verification code sent.'})
        
    elif status == 'ALREADY_AUTHORIZED':
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        service = TelegramService(phone, API_ID, API_HASH)
        user = loop.run_until_complete(service.get_me())
        loop.run_until_complete(graceful_shutdown(loop))
        loop.close()
        if user:
             save_account(phone, user.username)
        return jsonify({'status': 'ok', 'message': 'Account already authorized and added.'})

    else:
        return jsonify({'status': 'error', 'message': 'Failed to start login process.'}), 500

@app.route('/api/accounts/finalize', methods=['POST'])
def finalize_account():
    phone = request.json.get('phone')
    code = request.json.get('code')
    password = request.json.get('password')
    
    if not phone:
         return jsonify({'status': 'error', 'message': 'Phone is required.'}), 400

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    service = TelegramService(phone, API_ID, API_HASH)
    status = ''

    try:
        if code:
            phone_code_hash = pending_hashes.get(phone)
            if not phone_code_hash:
                return jsonify({'status': 'error', 'message': 'Login session expired. Please try again.'}), 400
            status = loop.run_until_complete(service.submit_code(code, phone_code_hash))
        
        elif password:
            status = loop.run_until_complete(service.submit_password(password))

        else:
            return jsonify({'status': 'error', 'message': 'Code or password is required.'}), 400

        if status == 'SUCCESS':
            user = loop.run_until_complete(service.get_me())
            if user:
                save_account(phone, user.username)
            if phone in pending_hashes: del pending_hashes[phone]
            return jsonify({'status': 'ok', 'message': 'Account connected successfully!'})
            
        elif status == 'PASSWORD_NEEDED':
            return jsonify({'status': 'ok', 'message': '2FA password required.'})
            
        else:
            if phone in pending_hashes: del pending_hashes[phone]
            return jsonify({'status': 'error', 'message': f'Login failed: {status}'}), 500

    finally:
        if not loop.is_closed():
            loop.run_until_complete(graceful_shutdown(loop))
            loop.close()

@app.route('/api/accounts/delete', methods=['POST'])
def delete_account_route():
    phone = request.json.get('phone')
    if not phone:
        return jsonify({'status': 'error', 'message': 'Phone number is required.'}), 400

    accounts = load_accounts()
    updated_accounts = [acc for acc in accounts if acc['phone'] != phone]

    if len(accounts) == len(updated_accounts):
        return jsonify({'status': 'error', 'message': 'Account not found.'}), 404

    save_accounts(updated_accounts)

    session_file = os.path.join(SESSIONS_DIR, f"{phone.replace('+', '')}.session")
    if os.path.exists(session_file):
        os.remove(session_file)

    return jsonify({'status': 'ok', 'message': 'Account deleted successfully.'})

@app.route('/api/audience/scrape', methods=['POST'])
def scrape_audience_route():
    phone = request.json.get('phone')
    chat_link = request.json.get('chat_link')

    if not phone or not chat_link:
        return jsonify({'status': 'error', 'message': 'Phone and chat link are required.'}), 400

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    service = TelegramService(phone, API_ID, API_HASH)
    status, users = loop.run_until_complete(service.get_chat_participants(chat_link))
    loop.run_until_complete(graceful_shutdown(loop))
    loop.close()

    if status == "SUCCESS":
        return jsonify({'status': 'ok', 'users': users})
    else:
        error_message = status
        if 'No object found for' in status:
            error_message = f"Could not find the chat '{chat_link}'. Please check the username/link or make sure the selected account has joined it."
        elif 'A wait of' in status and 'seconds is required' in status:
             error_message = f"Too many requests (Flood Wait). Please wait a moment before trying again."
        elif 'Client not authorized' in status:
            error_message = "Authorization for this account has expired. Please delete and re-add the account."
        return jsonify({'status': 'error', 'message': error_message}), 500

# --- Web Page Routes ---

@app.route('/')
def index():
    return render_template('index.html')
