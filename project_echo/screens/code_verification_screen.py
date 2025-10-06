import asyncio

from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivymd.uix.screen import MDScreen

# FIX: Removed Builder call. All KV files will be loaded centrally in main.py

class CodeVerificationScreen(MDScreen):
    """The code verification screen, refactored for asynchronous operation."""

    def on_pre_enter(self, *args):
        """Clear fields and set focus when the screen is shown."""
        self.app = MDApp.get_running_app()
        self.ids.code_field.text = ""
        self.ids.password_field.text = ""
        self.ids.password_field.hint_text = "2FA Password (if any)"
        self.ids.password_field.disabled = True
        self.ids.spinner.active = False
        self.ids.code_field.focus = True

    def verify_code(self):
        """Starts the asynchronous code verification process."""
        asyncio.create_task(self.verify_code_async())

    async def verify_code_async(self):
        """The async part of the verification. Calls the telegram service."""
        self.ids.spinner.active = True
        code = self.ids.code_field.text
        password = self.ids.password_field.text

        password_to_send = password if not self.ids.password_field.disabled and password else None

        result = await self.app.telegram_service.verify_code(code, password_to_send)

        self.ids.spinner.active = False

        if result.get("success"):
            self.show_dialog("Success!", "You have successfully logged in.")
            await self.app.telegram_service.disconnect()
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
