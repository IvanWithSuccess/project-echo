from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.app import App
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button

class PasswordVerificationScreen(Screen):
    """
    Screen for entering the Two-Factor Authentication (2FA) password.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()
        self.error_popup = None

    def on_enter(self, *args):
        # Clear previous state
        self.ids.spinner_label.text = ""
        self.ids.password_field.text = ""

    def verify_password(self):
        """Initiates the password verification process."""
        password = self.ids.password_field.text
        if not password:
            self.show_error_popup("Please enter your password.")
            return

        self.ids.spinner_label.text = "Signing in..."
        self.app.run_async(self.async_verify_password(password))

    async def async_verify_password(self, password):
        """Asynchronously calls the Telegram service to verify the password."""
        result = await self.app.telegram_service.verify_password(
            session_string=self.app.session_string_for_password, # The session string from the previous step
            password=password
        )
        Clock.schedule_once(lambda dt: self.process_password_result(result))

    def process_password_result(self, result):
        """Handles the result from the password verification."""
        self.ids.spinner_label.text = ""

        if result.get("success"):
            # On success, the final session string is returned
            self.app.save_session(self.app.phone_to_verify, result["session_string"])
        else:
            # On failure, show an error message
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

        self.error_popup = Popup(title="Sign-In Failed", content=content, size_hint=(0.8, 0.4))
        ok_button.bind(on_release=self.error_popup.dismiss)
        self.error_popup.open()
