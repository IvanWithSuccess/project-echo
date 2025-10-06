import asyncio
import os
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PasswordHashInvalidError

from project_echo.config import API_ID, API_HASH


class TelegramService:
    """Handles all interactions with the Telegram API."""

    def __init__(self):
        self.sessions_dir = "sessions"
        os.makedirs(self.sessions_dir, exist_ok=True)
        self.clients = {}

    async def _get_client(self, phone):
        """Gets a client, ensuring it's stored per phone number."""
        if phone not in self.clients:
            session_path = os.path.join(self.sessions_dir, f"{phone}.session")
            self.clients[phone] = TelegramClient(session_path, API_ID, API_HASH)
        return self.clients[phone]

    async def send_code(self, phone):
        """Sends a verification code to the user's phone."""
        client = await self._get_client(phone)
        try:
            if not client.is_connected():
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
        FIXED: Correctly handles the 2FA flow by managing the client connection state.
        The client is no longer disconnected prematurely while waiting for a password.
        """
        client = await self._get_client(phone)
        try:
            if not client.is_connected():
                await client.connect()

            # If no password is given, this is the first attempt.
            if not password:
                try:
                    await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
                except SessionPasswordNeededError:
                    # Correctly signal the UI that a password is needed. DO NOT DISCONNECT.
                    hint = await client.get_password_hint()
                    return {"password_needed": True, "hint": hint}

            # If a password is provided, try to sign in with it.
            if password:
                try:
                    await client.sign_in(password=password)
                except PasswordHashInvalidError:
                    return {"success": False, "error": "Invalid password. Please try again."}

            # If we are here, we should be logged in.
            if await client.is_user_authorized():
                session_string = client.session.save()
                await client.disconnect() # Disconnect only on final success.
                return {"success": True, "session_string": session_string}
            else:
                # This path should not be hit with correct logic, but acts as a fallback.
                return {"success": False, "error": "An unknown authorization error occurred."}

        except PhoneCodeInvalidError:
            await client.disconnect() # Disconnect on definitive failure.
            return {"success": False, "error": "The confirmation code is invalid."}
        except Exception as e:
            if client.is_connected():
                await client.disconnect() # Disconnect on any other exception.
            return {"success": False, "error": str(e)}
