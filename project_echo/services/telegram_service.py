import asyncio
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError

# It's better to have API credentials in one place and import them
from ..screens.login_screen import API_ID, API_HASH

class TelegramService:
    """
    An asynchronous service to handle all interactions with the Telegram API.
    This ensures the UI never freezes during network requests.
    """

    def __init__(self):
        self.client = None
        self._sent_code = None

    async def send_code(self, phone_number: str) -> dict:
        """
        Connects to Telegram and sends a verification code.
        
        Args:
            phone_number: The user's phone number.

        Returns:
            A dictionary with 'success': True or 'success': False and 'error': message.
        """
        try:
            # Create a new client for each login attempt to ensure clean sessions
            self.client = TelegramClient(phone_number, API_ID, API_HASH)
            await self.client.connect()

            if await self.client.is_user_authorized():
                return {"success": False, "error": "User is already authorized."}

            self._sent_code = await self.client.send_code_request(phone_number)
            return {"success": True}

        except Exception as e:
            print(f"[TelegramService] Error sending code: {e}")
            return {"success": False, "error": str(e)}

    async def verify_code(self, code: str, password: str = None) -> dict:
        """
        Verifies the code and logs the user in, handling 2FA.

        Args:
            code: The verification code received by the user.
            password: The 2FA password (if any).

        Returns:
            A dictionary indicating success, failure, or if a password is needed.
        """
        if not self.client or not self.client.is_connected():
            return {"success": False, "error": "Client not connected. Please try again."}

        try:
            await self.client.sign_in(code=code, phone_hash=self._sent_code.phone_code_hash)
            # If sign_in is successful without error, the user is in.
            return {"success": True}

        except PhoneCodeInvalidError:
            return {"success": False, "error": "Invalid verification code."}

        except SessionPasswordNeededError:
            # The user has 2FA enabled. If a password was not provided, ask for it.
            if not password:
                # Get the password hint
                hint = await self.client.get_password_hint()
                return {"success": False, "password_needed": True, "hint": hint}
            
            # If a password was provided, try to sign in with it.
            try:
                await self.client.sign_in(password=password)
                return {"success": True}
            except Exception as e:
                # This could be a "Password incorrect" error, which we can get from the exception string.
                return {"success": False, "error": str(e)}

        except Exception as e:
            print(f"[TelegramService] Error verifying code: {e}")
            return {"success": False, "error": str(e)}

        finally:
            # We should only disconnect if the process is fully complete or has failed terminally.
            # For 2FA, we need to stay connected.
            pass

    async def disconnect(self):
        """Disconnects the client if it's connected."""
        if self.client and self.client.is_connected():
            await self.client.disconnect()
