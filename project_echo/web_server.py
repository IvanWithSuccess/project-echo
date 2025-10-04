
import asyncio
import json
import os
import logging
from flask import Flask, jsonify, render_template, request
from project_echo.services.telegram_service import TelegramService

# --- Constants ---
ACCOUNTS_FILE = "accounts.json"
API_ID = 26947469
API_HASH = "731a222f9dd8b290db925a6a382159dd"

app = Flask(
    __name__,
    template_folder='templates',
    static_folder='static'
)

# --- State Management ---
# This is a simple in-memory store for phone_code_hash.
# In a production app, you'd use a more robust solution like Redis.
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

def save_account(phone, username):
    accounts = load_accounts()
    if not any(acc['phone'] == phone for acc in accounts):
        accounts.append({"phone": phone, "username": username})
        with open(ACCOUNTS_FILE, 'w') as f:
            json.dump(accounts, f, indent=2)

# --- API Routes ---

@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    return jsonify(load_accounts())

@app.route('/api/accounts/add', methods=['POST'])
def add_account():
    phone = request.json.get('phone')
    if not phone:
        return jsonify({'status': 'error', 'message': 'Phone number is required.'}), 400

    # Each request gets its own event loop to be thread-safe
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    service = TelegramService(phone, API_ID, API_HASH)
    status, phone_code_hash = loop.run_until_complete(service.start_login())
    loop.close()

    if status == 'CODE_SENT':
        pending_hashes[phone] = phone_code_hash  # Store the hash
        return jsonify({'status': 'ok', 'message': 'Verification code sent.'})
        
    elif status == 'ALREADY_AUTHORIZED':
        # If already authorized, we need a new loop to get user info
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        user = loop.run_until_complete(service.get_me())
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

    service = TelegramService(phone, API_ID, API_HASH)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
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

        # --- Handle results ---
        if status == 'SUCCESS':
            user = loop.run_until_complete(service.get_me())
            if user:
                save_account(phone, user.username)
            if phone in pending_hashes: del pending_hashes[phone] # Clean up
            return jsonify({'status': 'ok', 'message': 'Account connected successfully!'})
            
        elif status == 'PASSWORD_NEEDED':
            # The connection is kept alive by the service in this specific case
            return jsonify({'status': 'ok', 'message': '2FA password required.'})
            
        else:
            if phone in pending_hashes: del pending_hashes[phone] # Clean up failed attempt
            return jsonify({'status': 'error', 'message': f'Login failed: {status}'}), 500

    finally:
        # Ensure the loop is always closed
        if not loop.is_closed():
            loop.close()

# --- Web Page Routes ---

@app.route('/')
def index():
    return render_template('index.html')
