import asyncio
import threading
from kivy.clock import Clock
from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivymd.uix.screen import MDScreen


class PasswordVerificationScreen(MDScreen):
    """Handles 2FA password entry using the new stateless service."""

    def on_pre_enter(self, *args):
        self.app = MDApp.get_running_app()
        self.ids.password_field.text = ""
        self.ids.spinner.active = False
        self.ids.password_field.focus = True
        hint = self.app.password_hint or "Password"
        self.ids.info_label.text = f"Your account is protected. Please enter your password.\nHint: {hint}"

    def verify_password(self):
        self.ids.spinner.active = True
        threading.Thread(target=self.run_async_verification, daemon=True).start()

    def run_async_verification(self):
        try:
            result = asyncio.run(self.verify_password_async())
        except Exception as e:
            result = {"success": False, "error": str(e)}
        Clock.schedule_once(lambda dt: self.process_verification_result(result))

    async def verify_password_async(self):
        password = self.ids.password_field.text
        # Use the session string passed from the previous screen
        return await self.app.telegram_service.verify_code(
            session_string=self.app.session_string,
            phone=self.app.phone_to_verify, # Keep passing phone for context if needed
            code=None,  # Not needed for this step
            phone_code_hash=self.app.phone_code_hash, # Keep passing hash
            password=password
        )

    def process_verification_result(self, result):
        self.ids.spinner.active = False
        if result.get("success"):
            # Final session string after successful login
            self.app.save_session(self.app.phone_to_verify, result["session_string"])
            self.show_dialog("Success!", "You have successfully logged in.")
            self.app.switch_screen('accounts')
        else:
            error_message = result.get("error", "An unknown error occurred.")
            self.show_dialog("Verification Failed", error_message)

    def show_dialog(self, title, text):
        dialog = MDDialog(
            title=title, text=text,
            buttons=[MDFlatButton(text="OK", on_release=lambda *args: dialog.dismiss())]
        )
        dialog.open()
