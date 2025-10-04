
import logging
import os
from telethon import TelegramClient, functions, types
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.functions.photos import UploadProfilePhotoRequest
from telethon.errors import SessionPasswordNeededError

SESSIONS_DIR = "sessions"
UPLOADS_DIR = "uploads"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TelegramService:
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

    async def start_login(self) -> (str, str | None):
        logging.info(f"[{self.session_name}] Connecting for login...")
        await self.client.connect()
        status, phone_code_hash = None, None
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
                status, phone_code_hash = 'ERROR', str(e)
        await self.client.disconnect()
        return status, phone_code_hash

    async def submit_code(self, code: str, phone_code_hash: str) -> str:
        logging.info(f"[{self.session_name}] Connecting to submit code...")
        await self.client.connect()
        status = ''
        try:
            await self.client.sign_in(self.phone, code, phone_code_hash=phone_code_hash)
            status = 'SUCCESS'
        except SessionPasswordNeededError:
            status = 'PASSWORD_NEEDED'
        except Exception as e:
            status = str(e)
        if status != 'PASSWORD_NEEDED': await self.client.disconnect()
        return status

    async def submit_password(self, password: str) -> str:
        if not self.client.is_connected(): await self.client.connect()
        status = ''
        try:
            await self.client.sign_in(password=password)
            status = 'SUCCESS'
        except Exception as e:
            status = str(e)
        await self.client.disconnect()
        return status

    async def get_me(self):
        await self.client.connect()
        user = await self.client.get_me() if await self.client.is_user_authorized() else None
        await self.client.disconnect()
        return user

    async def get_chat_participants(self, chat_link: str) -> (str, list):
        logging.info(f"[{self.session_name}] Connecting to scrape: {chat_link}")
        await self.client.connect()
        users, status = [], ""
        try:
            if not await self.client.is_user_authorized(): raise Exception("Client not authorized.")
            entity = await self.client.get_entity(chat_link)
            async for user in self.client.iter_participants(entity, limit=None):
                if not user.bot and not user.deleted:
                    users.append({"id": user.id, "username": user.username, "first_name": user.first_name, "last_name": user.last_name})
            status = "SUCCESS"
        except Exception as e:
            status = str(e)
        finally:
            await self.client.disconnect()
        return status, users
    
    async def send_message(self, user_id: int, message: str) -> str:
        logging.info(f"[{self.session_name}] Connecting to send message to {user_id}...")
        await self.client.connect()
        status = ""
        try:
            if not await self.client.is_user_authorized(): raise Exception("Client not authorized.")
            await self.client.send_message(user_id, message)
            status = "SUCCESS"
        except Exception as e:
            status = str(e)
        finally:
            await self.client.disconnect()
        return status

    async def update_profile(self, first_name: str, last_name: str, bio: str, avatar_path: str) -> str:
        logging.info(f"[{self.session_name}] Connecting to update profile...")
        await self.client.connect()
        status_log = []
        try:
            if not await self.client.is_user_authorized(): raise Exception("Client not authorized.")
            
            await self.client(UpdateProfileRequest(first_name=first_name or '', last_name=last_name or '', about=bio or ''))
            status_log.append("Name/Bio updated.")

            if avatar_path and os.path.exists(avatar_path):
                avatar_file = await self.client.upload_file(avatar_path)
                await self.client(UploadProfilePhotoRequest(file=avatar_file))
                status_log.append("Avatar updated.")
            elif avatar_path:
                status_log.append(f"Avatar path '{avatar_path}' not found, skipping.")
            
            return f"Profile update successful: {' '.join(status_log)}"

        except Exception as e:
            return str(e)
        finally:
            await self.client.disconnect()
