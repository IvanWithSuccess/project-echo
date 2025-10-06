from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button

class LoginScreen(Screen):
    """Screen for user login with a phone number."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()
        self.error_popup = None

    def on_enter(self, *args):
        """Reset fields when the screen is shown."""
        self.ids.spinner_label.text = ""
        self.ids.phone_field.text = ""

    def send_code(self):
        """Validates phone number and initiates the Telegram code request."""
        phone_number = self.ids.phone_field.text.strip()

        if not phone_number:
            self.show_error_popup("Please enter your full phone number (e.g., +1234567890).")
            return
        
        # Basic validation: check if it starts with '+' and has more characters
        if not phone_number.startswith('+') or len(phone_number) < 5:
            self.show_error_popup("Invalid phone number format. Please include the country code (e.g., +1234567890).")
            return

        self.ids.spinner_label.text = "Sending code..."
        self.app.run_async(self.async_send_code(phone_number))

    async def async_send_code(self, phone):
        """Asynchronously calls the Telegram service."""
        result = await self.app.telegram_service.send_code(phone)
        Clock.schedule_once(lambda dt: self.process_send_code_result(result, phone))

    def process_send_code_result(self, result, phone):
        """Handles the result of the code request."""
        self.ids.spinner_label.text = ""
        if result.get("success"):
            self.app.phone_to_verify = phone
            self.app.phone_code_hash = result["phone_code_hash"]
            self.app.root.ids.screen_manager.current = 'code_verification'
        else:
            error_message = result.get("error", "An unknown error occurred.")
            self.show_error_popup(error_message)

    def show_error_popup(self, text):
        """Displays a generic error popup."""
        if self.error_popup and self.error_popup.content:
            self.error_popup.dismiss()

        content = BoxLayout(orientation='vertical', spacing='10dp', padding='10dp')
        content.add_widget(Label(text=text, halign='center', color=(0, 0, 0, 1)))
        ok_button = Button(text="OK", size_hint_y=None, height='44dp')
        content.add_widget(ok_button)

        self.error_popup = Popup(title="Error", content=content, size_hint=(0.8, 0.4))
        ok_button.bind(on_release=self.error_popup.dismiss)
        self.error_popup.open()
