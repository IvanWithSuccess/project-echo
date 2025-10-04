
import logging
import os
from telethon import TelegramClient
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.functions.photos import UploadProfilePhotoRequest
from telethon.errors import SessionPasswordNeededError

SESSIONS_DIR = "sessions"
UPLOADS_DIR = "uploads"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TelegramService:
    """
    A stateless service for interacting with Telegram.
    Each method is self-contained and manages its own connection.
    """
    def __init__(self, phone: str, api_id: int, api_hash: str, system_version: str = None, proxy: dict = None):
        if not os.path.exists(SESSIONS_DIR): os.makedirs(SESSIONS_DIR)
        if not os.path.exists(UPLOADS_DIR): os.makedirs(UPLOADS_DIR)
        
        self.phone = phone
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_name = phone.replace('+', '')
        session_path = os.path.join(SESSIONS_DIR, self.session_name)
        
        self.client = TelegramClient(session_path, self.api_id, self.api_hash,
                                   system_version=system_version or '4.16.30-vxCUSTOM',
                                   proxy=proxy)

    # ... (login, code, password, get_me methods are unchanged)
    async def start_login(self) -> (str, str | None):
        # ...
    async def submit_code(self, code: str, phone_code_hash: str) -> str:
        # ...
    async def submit_password(self, password: str) -> str:
        # ...
    async def get_me(self):
        # ...

    async def get_chat_participants(self, chat_link: str) -> (str, list):
        # ... (unchanged)

    async def send_message(self, user_id: int, message: str) -> str:
        # ... (unchanged)

    async def update_profile(self, first_name: str, last_name: str, bio: str, avatar_path: str) -> str:
        logging.info(f"[{self.session_name}] Connecting to update profile...")
        await self.client.connect()
        status_log = []
        try:
            if not await self.client.is_user_authorized():
                raise Exception("Client not authorized.")

            # Update Name and Bio
            await self.client(UpdateProfileRequest(
                first_name=first_name or '',
                last_name=last_name or '',
                about=bio or ''
            ))
            status_log.append("Name/Bio updated.")

            # Update Avatar
            if avatar_path and os.path.exists(avatar_path):
                logging.info(f"[{self.session_name}] Uploading new avatar from {avatar_path}")
                avatar_file = await self.client.upload_file(avatar_path)
                await self.client(UploadProfilePhotoRequest(file=avatar_file))
                status_log.append("Avatar updated.")
            elif avatar_path:
                status_log.append(f"Avatar path '{avatar_path}' not found, skipping.")
            
            return f"Profile update successful: {' '.join(status_log)}"

        except Exception as e:
            logging.error(f"[{self.session_name}] Failed to update profile: {e}")
            return str(e)
        finally:
            logging.info(f"[{self.session_name}] Disconnecting after profile update.")
            await self.client.disconnect()
