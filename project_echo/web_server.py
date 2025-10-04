
from flask import Flask, render_template, jsonify, request
import json
import os
import asyncio
from project_echo.telegram_service import TelegramService

ACCOUNTS_FILE = "accounts.json"

# Initialize the Flask app and the Telegram service
app = Flask(
    __name__, 
    template_folder='templates',
    static_folder='static'
)
telegram_service = TelegramService(ACCOUNTS_FILE)

# --- Helper Functions ---

def load_accounts():
    if not os.path.exists(ACCOUNTS_FILE):
        return []
    try:
        with open(ACCOUNTS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

# --- API Routes ---

@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    """API endpoint to get the list of accounts."""
    accounts = load_accounts()
    return jsonify(accounts)

@app.route('/api/accounts/add', methods=['POST'])
def add_account():
    """API endpoint to add a new Telegram account."""
    data = request.json
    phone = data.get('phone')
    api_id = data.get('api_id')
    api_hash = data.get('api_hash')

    if not all([phone, api_id, api_hash]):
        return jsonify({'status': 'error', 'message': 'Missing required fields.'}), 400

    try:
        # Since Flask runs in a sync context, we need to run the async code in a new event loop
        result = asyncio.run(telegram_service.add_account_interactive(phone, api_id, api_hash))
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/accounts/finalize', methods=['POST'])
def finalize_account():
    """API endpoint to finalize account addition with code or password."""
    data = request.json
    phone = data.get('phone')
    code = data.get('code')
    password = data.get('password')
    
    try:
        result = asyncio.run(telegram_service.finalize_connection(phone, code, password))
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# --- Web Page Routes ---

@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template('index.html')

