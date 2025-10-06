import json
from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.recycleview import RecycleView
from kivy.properties import StringProperty, ListProperty

# A simple view class for the items in the RecycleView
class CountryItem(Button):
    pass

class LoginScreen(Screen):
    selected_country_code = StringProperty(None)
    selected_country_name = StringProperty(None)
    countries = ListProperty([])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()
        self.error_popup = None
        self.country_dialog = None
        self.load_countries()

    def load_countries(self):
        try:
            with open("project_echo/countries.json", "r") as f:
                self.countries = json.load(f)
        except FileNotFoundError:
            print("Error: countries.json not found!")

    def on_enter(self, *args):
        self.ids.spinner_label.text = ""
        self.ids.phone_field.text = ""
        self.ids.country_button.text = self.selected_country_name or "Choose a Country"

    def send_code(self):
        phone_number = self.ids.phone_field.text
        if not self.selected_country_code:
            self.show_error_popup("Please choose a country.")
            return
        if not phone_number:
            self.show_error_popup("Please enter your phone number.")
            return

        full_phone = f"{self.selected_country_code}{phone_number}"
        self.ids.spinner_label.text = "Sending code..."
        self.app.run_async(self.async_send_code(full_phone))

    async def async_send_code(self, phone):
        result = await self.app.telegram_service.send_code(phone)
        Clock.schedule_once(lambda dt: self.process_send_code_result(result, phone))

    def process_send_code_result(self, result, phone):
        self.ids.spinner_label.text = ""
        if result.get("success"):
            self.app.phone_to_verify = phone
            self.app.phone_code_hash = result["phone_code_hash"]
            self.app.root.ids.screen_manager.current = 'code_verification'
        else:
            error_message = result.get("error", "An unknown error occurred.")
            self.show_error_popup(error_message)

    def show_country_dialog(self):
        if self.country_dialog:
            self.country_dialog.open()
            return

        # Main layout for the popup
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        
        # Search bar
        search_input = TextInput(hint_text="Search for a country...", size_hint_y=None, height=48)
        search_input.bind(text=self.filter_countries)
        
        # RecycleView for the country list
        rv = RecycleView(key_viewclass='viewclass', size_hint=(1, 1))
        rv.viewclass = 'CountryItem' # Using a simple Button
        self.update_country_list(rv, self.countries)

        content.add_widget(search_input)
        content.add_widget(rv)

        self.country_dialog = Popup(
            title="Choose a Country", 
            content=content, 
            size_hint=(0.9, 0.9)
        )
        self.country_dialog.open()

    def update_country_list(self, rv, country_list):
        rv.data = [
            {
                'text': f"{c['name']} (+{c['phone_code']})", 
                'on_release': lambda country=c: self.select_country(country),
                'size_hint_y': None,
                'height': 48,
                'background_color': (0.95, 0.95, 0.95, 1),
                'color': (0,0,0,1)
            } for c in country_list
        ]

    def filter_countries(self, instance, value):
        rv = instance.parent.children[0] # Find the RV in the popup content
        filtered_countries = [c for c in self.countries if value.lower() in c['name'].lower()]
        self.update_country_list(rv, filtered_countries)

    def select_country(self, country):
        self.selected_country_name = country['name']
        self.selected_country_code = country['phone_code']
        self.ids.country_button.text = self.selected_country_name
        self.country_dialog.dismiss()

    def show_error_popup(self, text):
        if self.error_popup:
            self.error_popup.dismiss()

        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        content.add_widget(Label(text=text, halign='center', color=(0,0,0,1)))
        ok_button = Button(text="OK", size_hint_y=None, height=44)
        content.add_widget(ok_button)

        self.error_popup = Popup(title="Login Failed", content=content, size_hint=(0.8, 0.4))
        ok_button.bind(on_release=self.error_popup.dismiss)
        self.error_popup.open()
