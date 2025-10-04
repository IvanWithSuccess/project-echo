
import asyncio
import json
import os
import logging
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

# --- Constants --- #
API_ID = 26947469
API_HASH = '731a222f9dd8b290db925a6a382159dd'
ACCOUNTS_FILE = "accounts.json"

# --- Logging --- #
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TelegramService:
    def __init__(self):
        self.active_clients = {}
        self.client_locks = {}

    def load_accounts(self):
        if not os.path.exists(ACCOUNTS_FILE):
            return []
        try:
            with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def save_accounts(self, accounts):
        with open(ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(accounts, f, indent=4, ensure_ascii=False)

    async def get_client(self, session_name, proxy_info=None):
        lock = self.client_locks.setdefault(session_name, asyncio.Lock())
        async with lock:
            if session_name in self.active_clients:
                client = self.active_clients[session_name]
                if client.is_connected() and await client.is_user_authorized():
                    return client
            
            client = TelegramClient(session_name, API_ID, API_HASH, proxy=proxy_info)
            await client.connect()
            if await client.is_user_authorized():
                self.active_clients[session_name] = client
                return client
            return None # Auth failed

    async def disconnect_client(self, session_name):
        lock = self.client_locks.get(session_name)
        if not lock: return
        async with lock:
            client = self.active_clients.pop(session_name, None)
            if client and client.is_connected():
                await client.disconnect()

    async def disconnect_all(self):
        await asyncio.gather(*(self.disconnect_client(name) for name in list(self.active_clients.keys())))

    # TODO: Add login/signup methods here

# Instantiate a singleton service
telegram_service = TelegramService()
