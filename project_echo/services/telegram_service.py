
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

        async def add_account(self, phone, on_code_request, on_password_request, on_success, on_failure):
            """Handles the entire asynchronous login flow."""
            session_name = phone.replace('+', '')
            client = TelegramClient(session_name, API_ID, API_HASH)
            
            try:
                await client.connect()
                phone_code_hash = None
    
                # --- Step 1: Send code --- #
                logging.info(f'[{session_name}] Sending code request...')
                result = await client.send_code_request(phone)
                phone_code_hash = result.phone_code_hash
                await on_code_request()
    
                # --- Step 2: Define what to do with the code --- #
                async def submit_code(code):
                    logging.info(f'[{session_name}] Submitting code...')
                    try:
                        await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
                        # If we are here, login was successful without 2FA
                        await on_login_success()
                    except SessionPasswordNeededError:
                        logging.info(f'[{session_name}] Password needed.')
                        await on_password_request()
                    except Exception as e:
                        logging.error(f'[{session_name}] Code submission error: {e}')
                        await on_failure(str(e))
                
                # --- Step 3: Define what to do with the password --- #
                async def submit_password(password):
                    logging.info(f'[{session_name}] Submitting password...')
                    try:
                        await client.sign_in(password=password)
                        # If we are here, 2FA login was successful
                        await on_login_success()
                    except Exception as e:
                        logging.error(f'[{session_name}] Password submission error: {e}')
                        await on_failure(str(e))
    
                # --- Helper for successful login --- #
                async def on_login_success():
                    logging.info(f'[{session_name}] Login successful.')
                    self.active_clients[session_name] = client
                    accounts = self.load_accounts()
                    if not any(a['session_name'] == session_name for a in accounts):
                        accounts.append({
                            'session_name': session_name,
                            'phone': phone,
                            'status': 'active', # Mark as active
                            'tags': [],
                            'notes': ''
                        })
                        self.save_accounts(accounts)
                    await on_success()
    
                # Return the handler functions to the UI
                return submit_code, submit_password
    
            except Exception as e:
                logging.error(f'[{session_name}] General error in add_account: {e}')
                if client.is_connected():
                    await client.disconnect()
                await on_failure(str(e))
                return None, None

    async def delete_account(self, session_name):
            """Deletes an account's session file and removes it from the list."""
            logging.info(f'Attempting to delete account: {session_name}')
            
            # Disconnect and remove from active clients
            await self.disconnect_client(session_name)
            
            # Remove from the JSON file
            accounts = self.load_accounts()
            original_count = len(accounts)
            accounts_to_keep = [acc for acc in accounts if acc.get('session_name') != session_name]
            
            if len(accounts_to_keep) < original_count:
                self.save_accounts(accounts_to_keep)
                logging.info(f'Removed {session_name} from {ACCOUNTS_FILE}')
            else:
                logging.warning(f'{session_name} not found in {ACCOUNTS_FILE}')
    
            # Delete the session file
            session_filename = f'{session_name}.session'
            if os.path.exists(session_filename):
                try:
                    os.remove(session_filename)
                    logging.info(f'Successfully deleted session file: {session_filename}')
                except OSError as e:
                    logging.error(f'Error deleting session file {session_filename}: {e}')
            else:
                logging.warning(f'Session file not found, cannot delete: {session_filename}')

    def update_account_details(self, session_name, details_to_update):
            """Updates arbitrary details for a specific account."""
            accounts = self.load_accounts()
            account_found = False
            for acc in accounts:
                if acc.get('session_name') == session_name:
                    acc.update(details_to_update)
                    account_found = True
                    break
            
            if account_found:
                self.save_accounts(accounts)
                logging.info(f'Updated details for {session_name}')
            else:
                logging.warning(f'Could not find account {session_name} to update.')

    async def get_dialogs(self, session_name):
            """Fetches all dialogs (chats, channels) for a given account."""
            client = await self.get_client(session_name)
            if not client:
                logging.error(f'[get_dialogs] Could not get client for {session_name}')
                return []
            
            dialogs = []
            try:
                async for dialog in client.iter_dialogs():
                    dialogs.append({
                        'id': dialog.id,
                        'name': dialog.name,
                        'is_channel': dialog.is_channel,
                        'is_group': dialog.is_group,
                        'is_user': dialog.is_user
                    })
                return dialogs
            except Exception as e:
                logging.error(f'[get_dialogs] Error fetching dialogs for {session_name}: {e}')
                return []

# Instantiate a singleton service
telegram_service = TelegramService()
