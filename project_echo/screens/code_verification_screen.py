from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
import asyncio


class CodeVerificationScreen(Screen):
    """
    The screen where the user enters the code sent to their Telegram.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = MDApp.get_running_app()
        self.dialog = None

    def on_enter(self, *args):
        """
        Updates the info label when the screen is displayed.
        """
        self.ids.info_label.text = (
            f"Enter the code sent to {self.app.phone_to_verify}"
        )
        self.ids.spinner.active = False
        self.ids.code_field.text = ""

    def verify_code(self):
        """
        Handles the verification of the entered code.
        """
        code = self.ids.code_field.text
        if not code:
            self.show_error_dialog("Please enter the confirmation code.")
            return

        self.ids.spinner.active = True
        asyncio.create_task(self.async_verify_code(code))

    async def async_verify_code(self, code):
        """
        Asynchronously calls the Telegram service to verify the code.
        """
        result = await self.app.telegram_service.verify_code(
            session_string=self.app.session_string_for_password, # Use the temp session
            phone=self.app.phone_to_verify,
            code=code,
            phone_code_hash=self.app.phone_code_hash
        )
        Clock.schedule_once(lambda dt: self.process_verification_result(result))

    def process_verification_result(self, result):
        """
        Processes the result from the Telegram service.
        """
        self.ids.spinner.active = False
        if result.get("success"):
            # FIX: If successful and no password is needed, save the session
            self.app.save_session(self.app.phone_to_verify, result["session_string"])

        elif result.get("password_needed"):
            self.app.session_string_for_password = result["session_string"]
            password_screen = self.manager.get_screen('password_verification_screen')
            password_screen.ids.info_label.text = (
                f"Hint: {result.get('hint', 'No hint available')}"
            )
            self.app.switch_screen('password_verification_screen')
        else:
            self.show_error_dialog(result.get("error", "An unknown error occurred."))

    def show_error_dialog(self, text):
        """
        Displays an error dialog with the given text.
        """
        if not self.dialog:
            self.dialog = MDDialog(
                title="Verification Failed",
                text=text,
                buttons=[
                    MDFlatButton(
                        text="OK",
                        on_release=lambda x: self.dialog.dismiss()
                    ),
                ],
            )
        self.dialog.text = text
        self.dialog.open()
