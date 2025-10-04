
from flask import Flask, render_template, jsonify
import json
import os

ACCOUNTS_FILE = "accounts.json"

# Initialize the Flask app
app = Flask(
    __name__, 
    template_folder='templates',
    static_folder='static'
)

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

# --- Web Page Routes ---

@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template('index.html')
