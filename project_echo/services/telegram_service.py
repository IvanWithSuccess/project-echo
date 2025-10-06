import asyncio
import os
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PasswordHashInvalidError

from project_echo.config import API_ID, API_HASH


class TelegramService:
    """
    Handles interactions with the Telegram API in a stateless manner
    to prevent asyncio event loop conflicts.
    """

    def __init__(self):
        pass

    async def send_code(self, phone):
        """
        Creates a new client, sends the code, and returns the session state.
        """
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        try:
            await client.connect()
            if not await client.is_user_authorized():
                result = await client.send_code_request(phone)
                session_string = client.session.save()
                return {
                    "success": True,
                    "phone_code_hash": result.phone_code_hash,
                    "session_string": session_string,
                }
            else:
                return {"success": False, "error": "User is already authorized."}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            if client.is_connected():
                await client.disconnect()

    async def verify_code(self, session_string, phone, code, phone_code_hash, password=None):
        """
        Restores a client from a session string, verifies the code or password,
        and returns the result.
        """
        client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
        try:
            await client.connect()

            if not password:
                try:
                    await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
                # FIX: Correctly get hint from the exception object itself.
                except SessionPasswordNeededError as e:
                    updated_session_string = client.session.save()
                    return {
                        "password_needed": True,
                        "hint": e.hint, # Correct way to get the hint
                        "session_string": updated_session_string
                    }

            if password:
                try:
                    await client.sign_in(password=password)
                except PasswordHashInvalidError:
                    return {"success": False, "error": "Invalid password. Please try again."}

            if await client.is_user_authorized():
                final_session_string = client.session.save()
                return {"success": True, "session_string": final_session_string}
            else:
                return {"success": False, "error": "An unknown authorization error occurred."}

        except PhoneCodeInvalidError:
            return {"success": False, "error": "The confirmation code is invalid."}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            if client.is_connected():
                await client.disconnect()
