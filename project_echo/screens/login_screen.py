import threading
from functools import partial
from kivy.clock import Clock
from kivymd.uix.screen import MDScreen
from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivymd.uix.menu import MDDropdownMenu
from telethon.sync import TelegramClient

# IMPORTANT: Use your actual API credentials
API_ID = 26915228  # Replace with your API ID
API_HASH = "1a60155a09d3b44846c2432c255e4b2a"  # Replace with your API HASH

# FIX: Add a dictionary of countries and their codes
COUNTRY_DATA = {
    "Ukraine": "+380",
    "United States": "+1",
    "Germany": "+49",
    "Poland": "+48",
    "United Kingdom": "+44",
}

class LoginScreen(MDScreen):
    """Screen for logging into a Telegram account."""

    def on_enter(self):
        """Create the country selection dropdown menu when the screen is entered."""
        menu_items = [
            {
                "text": country,
                "viewclass": "OneLineListItem",
                "on_release": partial(self.set_country, country, code),
            } for country, code in COUNTRY_DATA.items()
        ]
        self.country_menu = MDDropdownMenu(
            caller=self.ids.country_field,
            items=menu_items,
            width_mult=4,
        )

    def open_country_menu(self):
        """Opens the dropdown menu."""
        self.country_menu.open()

    def set_country(self, country_name, country_code):
        """Sets the country and phone code when an item is selected from the menu."""
        self.ids.country_field.text = country_name
        self.ids.phone_field.text = country_code
        self.country_menu.dismiss()

    def on_next_button_press(self):
        """Shows spinner and starts the login worker thread."""
        self.ids.spinner.active = True
        phone_number = self.ids.phone_field.text
        threading.Thread(target=self._send_code_worker, args=(phone_number,), daemon=True).start()

    def _send_code_worker(self, phone_number):
        """Runs in a thread to handle network operations."""
        client = TelegramClient(phone_number, API_ID, API_HASH)

        try:
            client.connect()
            if not client.is_user_authorized():
                client.send_code_request(phone_number)
                MDApp.get_running_app().phone_to_verify = phone_number
                Clock.schedule_once(self._go_to_code_verification_screen)
            else:
                Clock.schedule_once(lambda dt: self.show_dialog("Already Authorized", "This account is already logged in."))
                Clock.schedule_once(self._go_to_accounts_screen)

        except Exception as e:
            Clock.schedule_once(lambda dt: self.show_dialog("Login Error", str(e)))
        finally:
            if client.is_connected():
                client.disconnect()
            Clock.schedule_once(lambda dt: setattr(self.ids.spinner, 'active', False))

    def _go_to_code_verification_screen(self, dt):
        MDApp.get_running_app().root.ids.screen_manager.current = 'code_verification_screen'

    def _go_to_accounts_screen(self, dt):
        MDApp.get_running_app().root.ids.screen_manager.current = 'accounts'

    def show_dialog(self, title, text):
        """Displays a dialog window on the main thread."""
        # Implementation for showing dialogs...
        if not hasattr(self, 'dialog') or not self.dialog:
            self.dialog = MDDialog(
                title=title,
                text=text,
                buttons=[
                    MDFlatButton(
                        text="OK",
                        on_release=lambda *args: self.dialog.dismiss()
                    ),
                ],
            )
        else:
            self.dialog.title = title
            self.dialog.text = text
        self.dialog.open()
