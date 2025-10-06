import asyncio
import threading
from kivy.clock import Clock
from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivymd.uix.screen import MDScreen
from project_echo.screens.password_verification_screen import PasswordVerificationScreen


class CodeVerificationScreen(MDScreen):
    """Handles code verification using the new stateless service."""

    def on_pre_enter(self, *args):
        self.app = MDApp.get_running_app()
        if not self.app.root.ids.screen_manager.has_screen('password_verification_screen'):
            self.app.root.ids.screen_manager.add_widget(PasswordVerificationScreen())

        self.ids.code_field.text = ""
        self.ids.spinner.active = False
        self.ids.code_field.focus = True
        self.ids.info_label.text = f"Enter the code sent to {self.app.phone_to_verify}"

    def verify_code(self):
        self.ids.spinner.active = True
        threading.Thread(target=self.run_async_verification, daemon=True).start()

    def run_async_verification(self):
        try:
            result = asyncio.run(self.verify_code_async())
        except Exception as e:
            result = {"success": False, "error": str(e)}
        Clock.schedule_once(lambda dt: self.process_verification_result(result))

    async def verify_code_async(self):
        code = self.ids.code_field.text
        return await self.app.telegram_service.verify_code(
            session_string=self.app.session_string,
            phone=self.app.phone_to_verify,
            code=code,
            phone_code_hash=self.app.phone_code_hash,
            password=None
        )

    def process_verification_result(self, result):
        self.ids.spinner.active = False

        if result.get("success"):
            # Final session string after successful login
            self.app.save_session(self.app.phone_to_verify, result["session_string"])
            self.show_dialog("Success!", "You have successfully logged in.")
            self.app.switch_screen('accounts')
        elif result.get("password_needed"):
            # IMPORTANT: Update the session string before switching screens
            self.app.session_string = result["session_string"]
            self.app.password_hint = result.get("hint", "")
            self.app.switch_screen('password_verification_screen')
        else:
            error_message = result.get("error", "An unknown error occurred.")
            self.show_dialog("Verification Failed", error_message)

    def show_dialog(self, title, text):
        dialog = MDDialog(
            title=title, text=text,
            buttons=[MDFlatButton(text="OK", on_release=lambda *args: dialog.dismiss())]
        )
        dialog.open()
