import asyncio

from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivymd.uix.screen import MDScreen


class CodeVerificationScreen(MDScreen):
    """The code verification screen, refactored for asynchronous operation and stability."""

    def on_pre_enter(self, *args):
        self.app = MDApp.get_running_app()
        self.ids.code_field.text = ""
        self.ids.password_field.text = ""
        self.ids.password_field.disabled = True
        self.ids.spinner.active = False
        self.ids.code_field.focus = True
        self.ids.info_label.text = f"Enter the code sent to {self.app.phone_to_verify}"

    def verify_code(self):
        """
        FIX: Uses asyncio.run to correctly start the async task from sync Kivy code.
        """
        try:
            asyncio.run(self.verify_code_async())
        except RuntimeError as e:
            print(f"Ignoring nested asyncio loop error: {e}")

    async def verify_code_async(self):
        """The async part of the verification. Calls the telegram service."""
        self.ids.spinner.active = True
        code = self.ids.code_field.text
        password = self.ids.password_field.text
        phone = self.app.phone_to_verify
        phone_code_hash = self.app.phone_code_hash

        password_to_send = password if not self.ids.password_field.disabled and password else None

        # FIX: Pass the phone_code_hash to the verification method.
        result = await self.app.telegram_service.verify_code(phone, code, phone_code_hash, password_to_send)

        self.ids.spinner.active = False

        if result.get("success"):
            self.show_dialog("Success!", "You have successfully logged in.")
            # Switch to accounts and trigger a refresh
            self.app.switch_screen('accounts')
        elif result.get("password_needed"):
            self.ids.password_field.disabled = False
            hint = result.get("hint", "Password required")
            self.ids.password_field.hint_text = hint
            self.ids.password_field.focus = True
            self.show_dialog("Password Needed", f"Your account is protected by a password.\nHint: {hint}")
        else:
            error_message = result.get("error", "An unknown error occurred.")
            self.show_dialog("Verification Failed", error_message)

    def show_dialog(self, title, text):
        """Helper to show a simple dialog."""
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
