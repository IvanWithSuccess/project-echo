import threading
from kivy.clock import Clock
from kivymd.uix.screen import MDScreen
from kivymd.app import MDApp
from telethon.sync import TelegramClient

# =============================================================================
# IMPORTANT: REPLACE WITH YOUR REAL API CREDENTIALS
# =============================================================================
# You MUST get your own api_id and api_hash from https://my.telegram.org
# The application will NOT work with these placeholder values.
API_ID = 12345678  # FIX: Replace with your API ID
API_HASH = "0123456789abcdef0123456789abcdef"  # FIX: Replace with your API HASH
# =============================================================================


class LoginScreen(MDScreen):
    """Screen for logging into a Telegram account."""

    def on_next_button_press(self):
        """Handles the logic when the 'NEXT' button is pressed."""
        phone_number = self.ids.phone_field.text
        
        # Run network operations in a separate thread to avoid freezing the UI
        threading.Thread(target=self._send_code_worker, args=(phone_number,), daemon=True).start()

    def _send_code_worker(self, phone_number):
        """This function runs in a separate thread."""
        print(f"[Login Worker] Attempting to connect for phone: {phone_number}")

        # Use the phone number as the session file name (e.g., "+380...")
        # This prevents Telethon from asking for input in the console.
        client = TelegramClient(phone_number, API_ID, API_HASH)

        try:
            client.connect()
            if not client.is_user_authorized():
                print("[Login Worker] User is not authorized. Sending code request...")
                client.send_code_request(phone_number)
                print("[Login Worker] Code sent successfully.")

                # We need to switch to the next screen on the main thread.
                # We store the phone number to pass it to the next screen.
                MDApp.get_running_app().phone_to_verify = phone_number
                Clock.schedule_once(self._go_to_code_verification_screen)
            else:
                print("[Login Worker] User is already authorized! Returning to accounts screen.")
                Clock.schedule_once(self._go_to_accounts_screen)

        except Exception as e:
            print(f"[Login Worker] An error occurred: {e}")
            # TODO: Display a user-friendly error dialog on the main thread
        finally:
            if client.is_connected():
                client.disconnect()
                print("[Login Worker] Disconnected.")
    
    def _go_to_code_verification_screen(self, dt):
        """Switches to the code verification screen (on the main thread)."""
        print("[Main Thread] Switching to code verification screen (not implemented yet).")
        # This is the next step in our development
        # MDApp.get_running_app().root.ids.screen_manager.current = 'code_verification_screen'

    def _go_to_accounts_screen(self, dt):
        """Switches back to the accounts screen (on the main thread)."""
        MDApp.get_running_app().root.ids.screen_manager.current = 'accounts'

