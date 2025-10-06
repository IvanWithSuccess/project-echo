import threading
from kivy.clock import Clock
from kivymd.uix.screen import MDScreen
from kivymd.app import MDApp
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError

# Import the API credentials from the login screen to ensure consistency
from .login_screen import API_ID, API_HASH


class CodeVerificationScreen(MDScreen):
    """Screen for entering the Telegram verification code and 2FA password."""

    def on_enter(self, *args):
        """Called when the screen is displayed."""
        # Automatically focus the code field when the screen opens
        self.ids.code_field.focus = True

    def verify_code(self):
        """Handles the logic when the 'CONFIRM' button is pressed."""
        code = self.ids.code_field.text
        password = self.ids.password_field.text

        # Retrieve the phone number that started the login process
        phone_number = MDApp.get_running_app().phone_to_verify

        if not phone_number:
            print("[Verify Worker] Error: No phone number found. Returning to login screen.")
            MDApp.get_running_app().root.ids.screen_manager.current = 'login_screen'
            return

        # Run network operations in a separate thread
        threading.Thread(
            target=self._verify_worker,
            args=(phone_number, code, password),
            daemon=True
        ).start()

    def _verify_worker(self, phone, code, password):
        """This function runs in a separate thread to verify the login details."""
        print(f"[Verify Worker] Connecting for {phone} to verify code.")
        client = TelegramClient(phone, API_ID, API_HASH)

        try:
            client.connect()
            print("[Verify Worker] Signing in...")
            
            client.sign_in(phone=phone, code=code, password=password if password else None)
            
            print("[Verify Worker] Sign in successful!")
            Clock.schedule_once(self._go_to_accounts_screen)

        except SessionPasswordNeededError:
            print("[Verify Worker] 2FA password is needed.")
            # TODO: Inform the user on the main thread that a password is required
        except Exception as e:
            print(f"[Verify Worker] An error occurred: {e}")
            # TODO: Show a user-friendly error on the main thread
        finally:
            if client.is_connected():
                client.disconnect()
                print("[Verify Worker] Disconnected.")
    
    def _go_to_accounts_screen(self, dt):
        """Switches back to the accounts screen (on the main thread)."""
        print("[Main Thread] Login successful, switching to accounts screen.")
        MDApp.get_running_app().root.ids.screen_manager.current = 'accounts'
