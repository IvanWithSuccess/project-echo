from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton

class PasswordVerificationScreen(Screen):
    """
    Screen for entering the two-factor authentication password.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = MDApp.get_running_app()
        self.dialog = None

    def on_enter(self, *args):
        self.ids.spinner.active = False
        self.ids.password_field.text = ""

    def verify_password(self):
        password = self.ids.password_field.text
        if not password:
            self.show_error_dialog("Please enter your password.")
            return

        self.ids.spinner.active = True
        # FIX: Use the new reliable async runner
        self.app.run_async(self.async_verify_password(password))

    async def async_verify_password(self, password):
        result = await self.app.telegram_service.verify_code(
            session_string=self.app.session_string_for_password,
            phone=self.app.phone_to_verify,
            code=None,  # No code needed at this stage
            phone_code_hash=self.app.phone_code_hash,
            password=password
        )
        Clock.schedule_once(lambda dt: self.process_verification_result(result))

    def process_verification_result(self, result):
        self.ids.spinner.active = False
        if result.get("success"):
            self.app.save_session(self.app.phone_to_verify, result["session_string"])
        else:
            error_message = result.get("error", "An unknown error occurred.")
            self.show_error_dialog(error_message)

    def show_error_dialog(self, text):
        if not self.dialog:
            self.dialog = MDDialog(
                title="Authentication Failed",
                text=text,
                buttons=[
                    MDFlatButton(
                        text="OK", on_release=lambda x: self.dialog.dismiss()
                    ),
                ],
            )
        self.dialog.text = text
        self.dialog.open()
