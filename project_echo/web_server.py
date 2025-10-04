
import asyncio
import json
import os
import logging
from flask import Flask, jsonify, render_template, request
from project_echo.services.telegram_service import TelegramService

ACCOUNTS_FILE = "accounts.json"

app = Flask(
    __name__,
    template_folder='templates',
    static_folder='static'
)

# --- State Management ---
# This is a simple in-memory store for pending logins. 
# In a production app, you'd use a more robust solution like Redis.
pending_logins = {}

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
    # Avoid duplicates
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

    service = TelegramService(phone)
    status = asyncio.run(service.start_login())

    if status == 'CODE_SENT':
        pending_logins[phone] = service  # Store the service instance
        return jsonify({'status': 'ok', 'message': 'Verification code sent.'})
        
    elif status == 'ALREADY_AUTHORIZED':
        user = asyncio.run(service.get_me())
        save_account(phone, user.username)
        asyncio.run(service.disconnect())
        return jsonify({'status': 'ok', 'message': 'Account already authorized and added.'})

    else:
        return jsonify({'status': 'error', 'message': 'Failed to start login process.'}), 500

@app.route('/api/accounts/finalize', methods=['POST'])
def finalize_account():
    phone = request.json.get('phone')
    code = request.json.get('code')
    password = request.json.get('password')
    
    if not phone or phone not in pending_logins:
        return jsonify({'status': 'error', 'message': 'No pending login found for this phone.'}), 404

    service = pending_logins[phone]
    status = ''

    try:
        if code:
            status = asyncio.run(service.submit_code(code))
        elif password:
            status = asyncio.run(service.submit_password(password))
        else:
            return jsonify({'status': 'error', 'message': 'Code or password is required.'}), 400

        if status == 'SUCCESS':
            user = asyncio.run(service.get_me())
            save_account(phone, user.username)
            del pending_logins[phone]
            asyncio.run(service.disconnect())
            return jsonify({'status': 'ok', 'message': 'Account connected successfully!'})
            
        elif status == 'PASSWORD_NEEDED':
            return jsonify({'status': 'ok', 'message': '2FA password required.'})
            
        else:
             # Handle other errors like wrong code
            del pending_logins[phone] # Clean up failed attempt
            asyncio.run(service.disconnect())
            return jsonify({'status': 'error', 'message': f'Login failed: {status}'}), 500

    except Exception as e:
        logging.error(f"Finalize error for {phone}: {e}")
        if phone in pending_logins:
            del pending_logins[phone]
            asyncio.run(service.disconnect())
        return jsonify({'status': 'error', 'message': str(e)}), 500

# --- Web Page Routes ---

@app.route('/')
def index():
    return render_template('index.html')
