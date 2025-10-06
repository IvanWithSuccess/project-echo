from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivymd.uix.list import OneLineAvatarIconListItem
from kivy.properties import StringProperty


class CountryListItem(OneLineAvatarIconListItem):
    code = StringProperty()


class LoginScreen(Screen):
    """Login screen for entering phone number."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = MDApp.get_running_app()
        self.dialog = None
        self.country_dialog = None

    def on_enter(self, *args):
        self.ids.spinner.active = False
        self.ids.country_field.text = ""
        self.ids.phone_field.text = ""
        self.ids.phone_field.bind(text=self.on_phone_text_change)

    def on_phone_text_change(self, instance, value):
        country_name = self.app.country_service.get_country_by_code(value)
        if country_name:
            self.ids.country_field.text = country_name

    def on_next_button_press(self):
        country = self.ids.country_field.text
        phone = self.ids.phone_field.text

        if not country or not phone:
            self.show_error_dialog("Country and phone number are required.")
            return

        # FIX: Use the correct method name `get_country_code`
        full_phone = phone if phone.startswith('+') else f"{self.app.country_service.get_country_code(country)}{phone}"
        self.app.phone_to_verify = full_phone
        self.ids.spinner.active = True

        self.app.run_async(self.async_send_code(full_phone))

    async def async_send_code(self, phone):
        result = await self.app.telegram_service.send_code(phone)
        Clock.schedule_once(lambda dt: self.process_send_code_result(result))

    def process_send_code_result(self, result):
        self.ids.spinner.active = False
        if result.get("success"):
            self.app.phone_code_hash = result["phone_code_hash"]
            self.app.session_string_for_password = result["session_string"]
            self.app.switch_screen('code_verification_screen')
        else:
            self.show_error_dialog(result.get("error", "An unknown error occurred."))

    # FIX: Correctly unpack the tuple from `get_all_countries`
    def open_country_dialog(self):
        if not self.country_dialog:
            items = []
            # Correctly unpack (country_name, code) tuple
            for country_name, code in self.app.country_service.get_all_countries():
                item = CountryListItem(text=country_name, code=str(code) if code else "")
                item.bind(on_release=self.select_country)
                items.append(item)

            self.country_dialog = MDDialog(
                title="Choose a Country",
                type="simple",
                items=items,
            )
        self.country_dialog.open()

    def select_country(self, instance):
        self.ids.country_field.text = instance.text
        self.ids.phone_field.text = instance.code
        self.country_dialog.dismiss()

    def show_error_dialog(self, text):
        if not self.dialog:
            self.dialog = MDDialog(
                title="Login Error",
                text=text,
                buttons=[MDFlatButton(text="OK", on_release=lambda x: self.dialog.dismiss())]
            )
        self.dialog.text = text
        self.dialog.open()
