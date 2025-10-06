from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.app import App
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button

class CodeVerificationScreen(Screen):
    """
    The screen where the user enters the code sent to their Telegram.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()
        self.error_popup = None

    def on_enter(self, *args):
        self.ids.info_label.text = f"Enter the code sent to {self.app.phone_to_verify}"
        self.ids.spinner.active = False
        self.ids.code_field.text = ""

    def verify_code(self):
        code = self.ids.code_field.text
        if not code:
            self.show_error_popup("Please enter the confirmation code.")
            return

        self.ids.spinner.active = True
        self.app.run_async(self.async_verify_code(code))

    async def async_verify_code(self, code):
        """
        Asynchronously calls the Telegram service to verify the code.
        """
        result = await self.app.telegram_service.verify_code(
            session_string=self.app.session_string_for_password,
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
            self.app.save_session(self.app.phone_to_verify, result["session_string"])
        elif result.get("password_needed"):
            self.app.session_string_for_password = result["session_string"]
            password_screen = self.manager.get_screen('password_verification_screen')
            password_screen.ids.info_label.text = f"Hint: {result.get('hint', 'No hint available')}"
            self.app.switch_screen('password_verification_screen')
        else:
            self.show_error_popup(result.get("error", "An unknown error occurred."))

    def show_error_popup(self, text):
        """
        Displays an error popup with the given text.
        """
        if self.error_popup:
            self.error_popup.dismiss()

        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        content.add_widget(Label(text=text, halign='center'))
        ok_button = Button(text="OK", size_hint_y=None, height=44)
        content.add_widget(ok_button)

        self.error_popup = Popup(title="Verification Failed", content=content, size_hint=(0.8, 0.4))
        ok_button.bind(on_release=self.error_popup.dismiss)
        self.error_popup.open()
