from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.app import App
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button

class CodeVerificationScreen(Screen):
    """
    Screen for entering the code received via Telegram.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()
        self.error_popup = None

    def on_enter(self, *args):
        # Clear previous state
        self.ids.spinner_label.text = ""
        self.ids.code_field.text = ""
        # Update info label with the correct phone number
        self.ids.info_label.text = f"Enter the code sent to {self.app.phone_to_verify}"

    def verify_code(self):
        code = self.ids.code_field.text
        if not code:
            self.show_error_popup("Please enter the code.")
            return

        self.ids.spinner_label.text = "Verifying..."
        self.app.run_async(self.async_verify_code(code))

    async def async_verify_code(self, code):
        """Asynchronously calls the Telegram service to verify the code."""
        result = await self.app.telegram_service.verify_code(
            session_string=None,  # Not needed for the first step
            phone=self.app.phone_to_verify,
            code=code,
            phone_code_hash=self.app.phone_code_hash
        )
        Clock.schedule_once(lambda dt: self.process_verification_result(result))

    def process_verification_result(self, result):
        """Handles the result from the verification attempt."""
        self.ids.spinner_label.text = ""

        if result.get("success"):
            # On success, the session string is returned
            self.app.save_session(self.app.phone_to_verify, result["session_string"])

        elif result.get("password_required"):
            # If 2FA is enabled, we need to ask for the password
            self.app.session_string_for_password = result["session_string"]
            self.app.root.ids.screen_manager.current = 'password_verification_screen'
        else:
            # On failure, show an error
            error_message = result.get("error", "An unknown error occurred.")
            self.show_error_popup(error_message)

    def show_error_popup(self, text):
        """Displays an error message in a popup."""
        if self.error_popup:
            self.error_popup.dismiss()
        
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        content.add_widget(Label(text=text, halign='center', color=(0,0,0,1)))
        ok_button = Button(text="OK", size_hint_y=None, height=44)
        content.add_widget(ok_button)

        self.error_popup = Popup(title="Verification Failed", content=content, size_hint=(0.8, 0.4))
        ok_button.bind(on_release=self.error_popup.dismiss)
        self.error_popup.open()
