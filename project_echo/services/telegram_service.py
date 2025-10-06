import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeExpiredError, FloodWaitError
from project_echo.config import API_ID, API_HASH

class TelegramService:
    """
    A service for handling interactions with the Telegram API.
    """

    def __init__(self):
        self.active_clients = {}

    def get_client_for_phone(self, phone):
        """
        Gets or creates a client for a specific phone number to maintain session state.
        This is crucial for multi-step processes like login.
        """
        if phone not in self.active_clients:
            # Use an in-memory session for the initial login flow.
            # We will create a StringSession only after successful login.
            self.active_clients[phone] = TelegramClient(StringSession(), API_ID, API_HASH)
        return self.active_clients[phone]

    async def send_code(self, phone: str):
        """
        Sends a verification code to the user's Telegram account.
        Reuses the client to keep the session alive.
        """
        client = self.get_client_for_phone(phone)
        try:
            if not client.is_connected():
                await client.connect()
            
            # This sends the code and stores the hash for the next step.
            sent_code = await client.send_code_request(phone)
            return {
                "success": True,
                "phone_code_hash": sent_code.phone_code_hash
            }
        except FloodWaitError as e:
            return {"success": False, "error": f"Flood wait: please try again in {e.seconds} seconds."}
        except Exception as e:
            print(f"Error sending code: {e}")
            return {"success": False, "error": f"Failed to send code: {e}"}

    async def verify_code_and_get_session(self, phone: str, code: str, phone_code_hash: str):
        """
        Verifies the code and, if successful, returns the session string.
        Handles 2FA by returning a specific status.
        """
        client = self.get_client_for_phone(phone)
        try:
            if not client.is_connected():
                await client.connect()

            await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
            session_string = client.session.save()
            await client.disconnect()
            del self.active_clients[phone] # Clean up
            return {"success": True, "session_string": session_string}

        except SessionPasswordNeededError:
            # The user has 2FA enabled. We need to prompt for the password.
            # The current session is now authorized to accept a password.
            return {"success": False, "status": "2fa_needed"}
        
        except PhoneCodeExpiredError:
            return {"success": False, "error": "The confirmation code has expired."}
        except Exception as e:
            print(f"Error verifying code: {e}")
            await client.disconnect()
            del self.active_clients[phone] # Clean up
            return {"success": False, "error": f"Verification failed: {e}"}

    async def verify_password(self, phone: str, password: str):
        """
        Verifies the 2FA password and returns the session string if successful.
        """
        client = self.get_client_for_phone(phone)
        try:
            if not client.is_connected():
                await client.connect()

            await client.sign_in(password=password)
            session_string = client.session.save()
            await client.disconnect()
            del self.active_clients[phone] # Clean up
            return {"success": True, "session_string": session_string}

        except Exception as e:
            print(f"Error verifying password: {e}")
            await client.disconnect()
            del self.active_clients[phone] # Clean up
            return {"success": False, "error": f"2FA login failed: {e}"}
