
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
    if not os.path.exists(file_path): return default if default is not None else []
    try:
        with open(file_path, 'r') as f: return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError): return default if default is not None else []

def save_json(file_path, data):
    with open(file_path, 'w') as f: json.dump(data, f, indent=2)

# --- HTML Routes ---
@app.route('/')
def index():
    return render_template('index.html')

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
    tag_name = request.json.get('name')
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

# --- The rest of the web_server.py file remains the same... ---
