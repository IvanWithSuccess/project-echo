import asyncio
import os
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError

from project_echo.config import API_ID, API_HASH


class TelegramService:
    """Handles all interactions with the Telegram API."""

    def __init__(self):
        self.sessions_dir = "sessions"
        os.makedirs(self.sessions_dir, exist_ok=True)
        self.clients = {}

    async def _get_client(self, phone):
        if phone not in self.clients:
            session_path = os.path.join(self.sessions_dir, f"{phone}.session")
            self.clients[phone] = TelegramClient(session_path, API_ID, API_HASH)
        return self.clients[phone]

    async def send_code(self, phone):
        client = await self._get_client(phone)
        try:
            await client.connect()
            if not await client.is_user_authorized():
                result = await client.send_code_request(phone)
                return {"success": True, "phone_code_hash": result.phone_code_hash}
            else:
                return {"success": False, "error": "User is already authorized."}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            if client.is_connected():
                await client.disconnect()

    async def verify_code(self, phone, code, phone_code_hash, password=None):
        """
        FIX: Handles 2FA (password) correctly by catching SessionPasswordNeededError
        and retrying the sign-in with the provided password.
        """
        client = await self._get_client(phone)
        try:
            await client.connect()
            await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)

            session_string = client.session.save()
            # The session file is already saved by the client, but the string can be stored elsewhere.
            return {"success": True, "session_string": session_string}

        except SessionPasswordNeededError as e:
            if password:
                try:
                    await client.sign_in(password=password)
                    session_string = client.session.save()
                    return {"success": True, "session_string": session_string}
                except Exception as e_pass:
                    return {"success": False, "error": str(e_pass)}
            else:
                # The UI needs to ask for the password. We can pass the hint along.
                hint = await client.get_password_hint()
                return {"success": False, "password_needed": True, "hint": hint}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            if client.is_connected():
                await client.disconnect()
