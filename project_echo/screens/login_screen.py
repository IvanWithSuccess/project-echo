from kivymd.uix.screen import MDScreen
from kivymd.app import MDApp
from telethon.sync import TelegramClient

# These need to be stored securely, not hardcoded
# For now, we'll define them here for development
API_ID = 26915228 # Replace with your real API ID
API_HASH = "1a60155a09d3b44846c2432c255e4b2a" # Replace with your real API HASH


class LoginScreen(MDScreen):
    """Screen for logging into a Telegram account."""

    def on_next_button_press(self):
        """Handles the logic when the 'NEXT' button is pressed."""
        phone_number = self.ids.phone_field.text
        print(f"[Login] Attempting to log in with phone: {phone_number}")

        # In a real app, you would handle this asynchronously to avoid freezing the UI.
        # For this example, we'll do it synchronously for simplicity.
        try:
            # Using a 'with' statement ensures the client is properly closed
            with TelegramClient(phone_number, API_ID, API_HASH) as client:
                print("[Login] Client Created. Sending code request...")
                # This will send a code to the user's Telegram account
                client.send_code_request(phone_number)
                print("[Login] Code sent successfully. Now we need a new screen to enter the code.")

                # TODO: Transition to a new screen to enter the received code, password, etc.
                # For now, we'll just print a success message.
                MDApp.get_running_app().root.ids.screen_manager.current = 'accounts'

        except Exception as e:
            print(f"[Login] An error occurred: {e}")
            # TODO: Display a user-friendly error dialog
