from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.app import App
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button

class PasswordVerificationScreen(Screen):
    """
    Screen for entering the two-factor authentication password.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()
        self.error_popup = None

    def on_enter(self, *args):
        self.ids.spinner.active = False
        self.ids.password_field.text = ""

    def verify_password(self):
        password = self.ids.password_field.text
        if not password:
            self.show_error_popup("Please enter your password.")
            return

        self.ids.spinner.active = True
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
            self.show_error_popup(error_message)

    def show_error_popup(self, text):
        if self.error_popup:
            self.error_popup.dismiss()

        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        content.add_widget(Label(text=text, halign='center'))
        ok_button = Button(text="OK", size_hint_y=None, height=44)
        content.add_widget(ok_button)

        self.error_popup = Popup(title="Authentication Failed", content=content, size_hint=(0.8, 0.4))
        ok_button.bind(on_release=self.error_popup.dismiss)
        self.error_popup.open()
