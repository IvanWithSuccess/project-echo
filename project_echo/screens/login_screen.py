
from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.app import App
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.recycleview import RecycleView
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.properties import ListProperty, StringProperty


# =============================================================================
# >> CUSTOM POPUP CONTENT
# =============================================================================

class CountryDialogPopup(Popup):
    """A custom popup for selecting a country with a search feature."""
    def __init__(self, login_screen, countries, **kwargs):
        super().__init__(**kwargs)
        self.login_screen = login_screen
        self.title = "Choose a Country"
        self.size_hint = (0.9, 0.9)

        # Main layout for the popup
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Search bar
        search_bar = TextInput(hint_text="Search for a country...", size_hint_y=None, height=48)
        search_bar.bind(text=self.filter_countries)
        layout.add_widget(search_bar)

        # RecycleView for the list of countries
        self.rv = RecycleView()
        self.rv.viewclass = 'Button'
        self.rv.data = []
        layout.add_widget(self.rv)

        self.content = layout
        self.filter_countries(search_bar, "") # Initial population

    def filter_countries(self, instance, search_text):
        """Filters the list of countries based on the search text."""
        self.login_screen.filter_countries(search_text, self.rv)

# =============================================================================
# >> LOGIN SCREEN
# =============================================================================

class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()
        self.error_popup = None
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
            self.show_error_popup("Country and phone number are required.")
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
            self.show_error_popup(result.get("error", "An unknown error occurred."))

    def open_country_dialog(self):
        if not self.country_dialog:
            self.country_dialog = CountryDialogPopup(self, self.all_countries)
        self.country_dialog.open()

    def filter_countries(self, search_text, recycle_view):
        if not search_text:
            countries_to_display = self.all_countries
        else:
            countries_to_display = self.app.country_service.search_countries(search_text)
        
        recycle_view.data = [
            {
                'text': f"{name} ({code})",
                'on_release': lambda name=name, code=code: self.select_country(name, code),
                'size_hint_y': None,
                'height': 48
            }
            for name, code in countries_to_display
        ]

    def select_country(self, country_name, country_code):
        self.ids.country_field.text = country_name
        self.ids.phone_field.text = country_code
        if self.country_dialog:
            self.country_dialog.dismiss()

    def show_error_popup(self, text):
        if self.error_popup:
            self.error_popup.dismiss()

        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        content.add_widget(Label(text=text))
        ok_button = Button(text="OK", size_hint_y=None, height=44)
        content.add_widget(ok_button)

        self.error_popup = Popup(title="Login Error", content=content, size_hint=(0.8, 0.4))
        ok_button.bind(on_release=self.error_popup.dismiss)
        self.error_popup.open()
