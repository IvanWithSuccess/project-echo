import asyncio
import threading
from kivy.clock import Clock
from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivymd.uix.screen import MDScreen


class PasswordVerificationScreen(MDScreen):
    """Handles the 2FA password entry for Telegram login."""

    def on_pre_enter(self, *args):
        self.app = MDApp.get_running_app()
        self.ids.password_field.text = ""
        self.ids.spinner.active = False
        self.ids.password_field.focus = True
        hint = self.app.password_hint or "Password"
        self.ids.info_label.text = f"Your account is protected. Please enter your password.\nHint: {hint}"

    def verify_password(self):
        """Runs the async verification in a separate thread."""
        self.ids.spinner.active = True
        threading.Thread(target=self.run_async_verification, daemon=True).start()

    def run_async_verification(self):
        """Helper that runs the asyncio event loop in the thread."""
        try:
            result = asyncio.run(self.verify_password_async())
        except Exception as e:
            result = {"success": False, "error": str(e)}
        Clock.schedule_once(lambda dt: self.process_verification_result(result))

    async def verify_password_async(self):
        """The actual async logic for password verification."""
        password = self.ids.password_field.text
        # We reuse the existing client session from the previous step
        return await self.app.telegram_service.verify_code(
            phone=self.app.phone_to_verify,
            code=None,  # Not needed for this step
            phone_code_hash=None, # Not needed for this step
            password=password
        )

    def process_verification_result(self, result):
        """Updates the UI based on the verification result."""
        self.ids.spinner.active = False
        if result.get("success"):
            self.show_dialog("Success!", "You have successfully logged in.")
            self.app.switch_screen('accounts')
        else:
            error_message = result.get("error", "An unknown error occurred.")
            self.show_dialog("Verification Failed", error_message)

    def show_dialog(self, title, text):
        if not hasattr(self, 'dialog') or not self.dialog:
            self.dialog = MDDialog(
                title=title,
                text=text,
                buttons=[MDFlatButton(text="OK", on_release=lambda *args: self.dialog.dismiss())],
            )
        else:
            self.dialog.title = title
            self.dialog.text = text
        self.dialog.open()
