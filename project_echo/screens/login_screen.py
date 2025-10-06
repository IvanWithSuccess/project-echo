from kivymd.uix.screen import MDScreen  # FIX: Inherit from MDScreen
from kivy.clock import Clock
from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivymd.uix.list import OneLineListItem
from kivy.properties import ListProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout


# =============================================================================
# >> DIALOG-RELATED CLASSES
# =============================================================================

class CountryDialogContent(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.screen = MDApp.get_running_app().root.get_screen('login_screen')

    def filter_countries(self, search_text):
        self.screen.filter_countries(search_text)

class CountryListItem(OneLineListItem):
    code = StringProperty()

    def select_country(self, instance):
        self.parent.parent.parent.parent.parent.screen.select_country(instance)


# =============================================================================
# >> LOGIN SCREEN
# =============================================================================

# FIX: Inherit from MDScreen to get theme properties
class LoginScreen(MDScreen):
    rv_data = ListProperty([])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = MDApp.get_running_app()
        self.dialog = None
        self.country_dialog = None
        self.all_countries = self.app.country_service.get_all_countries()

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

    def open_country_dialog(self):
        if not self.country_dialog:
            self.country_dialog = MDDialog(
                title="Choose a Country",
                type="custom",
                content_cls=CountryDialogContent(),
            )
        self.filter_countries("")
        self.country_dialog.open()

    def filter_countries(self, search_text=""):
        if not search_text:
            countries_to_display = self.all_countries
        else:
            countries_to_display = self.app.country_service.search_countries(search_text)
        
        self.country_dialog.content_cls.ids.rv.data = [
            {
                'viewclass': 'CountryListItem',
                'text': f"{name} ({code})",
                'code': code,
                'on_release': lambda x=code, y=name: self.select_country(y, x)
            }
            for name, code in countries_to_display
        ]

    def select_country(self, country_name, country_code):
        self.ids.country_field.text = country_name
        self.ids.phone_field.text = country_code
        if self.country_dialog:
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
