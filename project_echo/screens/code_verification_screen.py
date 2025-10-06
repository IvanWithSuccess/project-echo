import threading
from kivy.clock import Clock
from kivymd.uix.screen import MDScreen
from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError

# Import the API credentials
from .login_screen import API_ID, API_HASH


class CodeVerificationScreen(MDScreen):
    """Screen for entering the verification code and 2FA password."""

    def on_enter(self, *args):
        self.ids.code_field.focus = True
        # Clear fields when entering the screen
        self.ids.code_field.text = ""
        self.ids.password_field.text = ""
        self.ids.spinner.active = False

    def verify_code(self):
        """Shows spinner and starts the verification worker thread."""
        self.ids.spinner.active = True
        code = self.ids.code_field.text
        password = self.ids.password_field.text
        phone_number = MDApp.get_running_app().phone_to_verify

        if not phone_number:
            self.show_dialog("Error", "Phone number not found. Please go back and try again.")
            self.ids.spinner.active = False
            return

        threading.Thread(
            target=self._verify_worker,
            args=(phone_number, code, password),
            daemon=True
        ).start()

    def _verify_worker(self, phone, code, password):
        """Runs in a thread to verify the login details."""
        client = TelegramClient(phone, API_ID, API_HASH)

        try:
            client.connect()
            client.sign_in(phone=phone, code=code, password=password if password else None)
            Clock.schedule_once(self._go_to_accounts_screen)

        except PhoneCodeInvalidError:
            Clock.schedule_once(lambda dt: self.show_dialog("Invalid Code", "The confirmation code is incorrect."))
        except SessionPasswordNeededError:
            Clock.schedule_once(lambda dt: self.show_dialog("Password Needed", "Your account is protected with a 2FA password. Please enter it."))
        except Exception as e:
            Clock.schedule_once(lambda dt: self.show_dialog("Verification Error", str(e)))
        finally:
            if client.is_connected():
                client.disconnect()
            Clock.schedule_once(lambda dt: setattr(self.ids.spinner, 'active', False))

    def _go_to_accounts_screen(self, dt):
        """Switches back to the accounts screen on the main thread."""
        MDApp.get_running_app().root.ids.screen_manager.current = 'accounts'

    def show_dialog(self, title, text):
        """Utility function to display a dialog window."""
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
