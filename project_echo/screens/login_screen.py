from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton

class LoginScreen(Screen):
    """Login screen for entering phone number."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = MDApp.get_running_app()
        self.dialog = None

    def on_enter(self, *args):
        self.ids.spinner.active = False
        self.ids.country_field.text = ""
        self.ids.phone_field.text = ""

    def on_next_button_press(self):
        country = self.ids.country_field.text
        phone = self.ids.phone_field.text

        if not country or not phone:
            self.show_error_dialog("Country and phone number are required.")
            return
        
        full_phone = f"{self.app.country_service.get_country_code(country)}{phone}"
        self.app.phone_to_verify = full_phone
        self.ids.spinner.active = True
        
        # FIX: Use the new reliable async runner
        self.app.run_async(self.async_send_code(full_phone))

    async def async_send_code(self, phone):
        """Asynchronously sends the verification code."""
        result = await self.app.telegram_service.send_code(phone)
        Clock.schedule_once(lambda dt: self.process_send_code_result(result))

    def process_send_code_result(self, result):
        """Processes the result of the send code request."""
        self.ids.spinner.active = False
        if result.get("success"):
            self.app.phone_code_hash = result["phone_code_hash"]
            self.app.session_string_for_password = result["session_string"]
            self.app.switch_screen('code_verification_screen')
        else:
            self.show_error_dialog(result.get("error", "An unknown error occurred."))

    def open_country_dialog(self):
        # Implementation for country dialog remains the same
        pass

    def show_error_dialog(self, text):
        """Displays an error dialog."""
        if not self.dialog:
            self.dialog = MDDialog(
                title="Login Error",
                text=text,
                buttons=[MDFlatButton(text="OK", on_release=lambda x: self.dialog.dismiss())]
            )
        self.dialog.text = text
        self.dialog.open()
