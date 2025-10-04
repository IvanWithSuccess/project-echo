
import logging
import os
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

# App credentials provided by you
API_ID = 26947469
API_HASH = '731a222f9dd8b290db925a6a382159dd'
SESSIONS_DIR = "sessions"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TelegramService:
    def __init__(self, phone):
        if not os.path.exists(SESSIONS_DIR):
            os.makedirs(SESSIONS_DIR)
        
        self.session_name = phone.replace('+', '')
        session_path = os.path.join(SESSIONS_DIR, self.session_name)
        self.client = TelegramClient(session_path, API_ID, API_HASH)
        self.phone_code_hash = None

    async def disconnect(self):
        if self.client.is_connected():
            logging.info(f'[{self.session_name}] Disconnecting...')
            await self.client.disconnect()
            logging.info(f'[{self.session_name}] Disconnection complete!')

    async def start_login(self):
        logging.info(f'[{self.session_name}] Connecting...')
        await self.client.connect()
        if not await self.client.is_user_authorized():
            logging.info(f'[{self.session_name}] Sending code request...')
            try:
                result = await self.client.send_code_request(self.session_name)
                self.phone_code_hash = result.phone_code_hash
                return True
            except Exception as e:
                logging.error(f'[{self.session_name}] Failed to send code: {e}')
                await self.disconnect() # Disconnect on failure
                return False
        else:
            logging.info(f'[{self.session_name}] Already authorized.')
            return True

    async def submit_code(self, code):
        logging.info(f'[{self.session_name}] Submitting code...')
        try:
            await self.client.sign_in(self.session_name, code, phone_code_hash=self.phone_code_hash)
            return 'SUCCESS'
        except SessionPasswordNeededError:
            logging.info(f'[{self.session_name}] Password needed.')
            return 'PASSWORD_NEEDED'
        except Exception as e:
            logging.error(f'[{self.session_name}] Code submission error: {e}')
            return str(e)

    async def submit_password(self, password):
        logging.info(f'[{self.session_name}] Submitting password...')
        try:
            await self.client.sign_in(password=password)
            return 'SUCCESS'
        except Exception as e:
            logging.error(f'[{self.session_name}] Password submission error: {e}')
            return str(e)

    async def get_me(self):
        if not self.client.is_connected():
            await self.client.connect()
        if await self.client.is_user_authorized():
            return await self.client.get_me()
        return None
