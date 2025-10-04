
import logging
import os
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

SESSIONS_DIR = "sessions"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TelegramService:
    """
    A stateless service for interacting with Telegram.
    Each method is self-contained and manages its own connection.
    """
    def __init__(self, phone: str, api_id: int, api_hash: str):
        if not os.path.exists(SESSIONS_DIR):
            os.makedirs(SESSIONS_DIR)
        
        self.phone = phone
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_name = phone.replace('+', '')
        session_path = os.path.join(SESSIONS_DIR, self.session_name)
        self.client = TelegramClient(session_path, self.api_id, self.api_hash)

    async def start_login(self) -> (str, str | None):
        """
        Connects, starts the login process, and returns the status and phone_code_hash.
        """
        logging.info(f"[{self.session_name}] Connecting for login...")
        await self.client.connect()
        
        status = None
        phone_code_hash = None

        if await self.client.is_user_authorized():
            logging.info(f"[{self.session_name}] Already authorized.")
            status = 'ALREADY_AUTHORIZED'
        else:
            logging.info(f"[{self.session_name}] Sending code request...")
            try:
                result = await self.client.send_code_request(self.phone)
                phone_code_hash = result.phone_code_hash
                status = 'CODE_SENT'
            except Exception as e:
                logging.error(f"[{self.session_name}] Failed to send code: {e}")
                status = 'ERROR'

        logging.info(f"[{self.session_name}] Disconnecting after login start.")
        await self.client.disconnect()
        return status, phone_code_hash

    async def submit_code(self, code: str, phone_code_hash: str) -> str:
        """
        Connects, submits the verification code, and returns the result.
        """
        logging.info(f"[{self.session_name}] Connecting to submit code...")
        await self.client.connect()
        status = ''
        try:
            await self.client.sign_in(self.phone, code, phone_code_hash=phone_code_hash)
            status = 'SUCCESS'
        except SessionPasswordNeededError:
            logging.info(f"[{self.session_name}] Password needed.")
            status = 'PASSWORD_NEEDED'
        except Exception as e:
            logging.error(f"[{self.session_name}] Code submission error: {e}")
            status = str(e)
        
        # Don't disconnect if password is needed, we'll use the same connection
        if status != 'PASSWORD_NEEDED':
            logging.info(f"[{self.session_name}] Disconnecting after code submission.")
            await self.client.disconnect()

        return status

    async def submit_password(self, password: str) -> str:
        """
        Connects (or uses existing connection), submits the 2FA password, and returns the result.
        """
        if not self.client.is_connected():
            logging.info(f"[{self.session_name}] Connecting to submit password...")
            await self.client.connect()
        
        status = ''
        try:
            await self.client.sign_in(password=password)
            status = 'SUCCESS'
        except Exception as e:
            logging.error(f"[{self.session_name}] Password submission error: {e}")
            status = str(e)
        
        logging.info(f"[{self.session_name}] Disconnecting after password submission.")
        await self.client.disconnect()
        return status

    async def get_me(self):
        """
        Connects, gets user info, and disconnects.
        """
        logging.info(f"[{self.session_name}] Connecting to get user info...")
        await self.client.connect()
        user = None
        if await self.client.is_user_authorized():
            user = await self.client.get_me()
        
        logging.info(f"[{self.session_name}] Disconnecting after getting user info.")
        await self.client.disconnect()
        return user
