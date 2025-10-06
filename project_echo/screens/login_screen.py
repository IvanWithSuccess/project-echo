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


class LoginScreen(Screen):
    """Screen for user login, including country selection and phone number input."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()
        self.error_popup = None
        self.country_dialog = None
        self.all_countries = [] # To hold the full list from the service

    def on_enter(self, *args):
        """Reset fields when the screen is shown."""
        self.ids.spinner_label.text = ""
        self.ids.phone_field.text = ""
        # Use a more descriptive default text
        self.ids.country_button.text = "Select Country"
        # Load countries from the service when the screen is entered
        self.all_countries = self.app.country_service.get_all_countries()

    def send_code(self):
        """Validates input and initiates the Telegram code request."""
        phone_number = self.ids.phone_field.text
        country_code = self.app.get_country_code(self.ids.country_button.text)

        if not country_code:
            self.show_error_popup("Please select a country.")
            return
        if not phone_number:
            self.show_error_popup("Please enter your phone number.")
            return

        full_phone = f"{country_code}{phone_number}"
        self.ids.spinner_label.text = "Sending code..."
        # Use the app's async runner
        self.app.run_async(self.async_send_code(full_phone))

    async def async_send_code(self, phone):
        """Asynchronously calls the Telegram service."""
        result = await self.app.telegram_service.send_code(phone)
        # Schedule UI updates on the main thread
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

    def show_country_dialog(self):
        """Displays a popup dialog for selecting a country."""
        if not self.country_dialog:
            content = BoxLayout(orientation='vertical', spacing='10dp', padding='10dp')
            search_input = TextInput(hint_text="Search...", size_hint_y=None, height='48dp')
            search_input.bind(text=self.on_search_text)
            
            rv = RecycleView(size_hint_y=1)
            rv.viewclass = 'Button'
            rv.data = [] # Initially empty

            content.add_widget(search_input)
            content.add_widget(rv)

            self.country_dialog = Popup(
                title="Select a Country",
                content=content,
                size_hint=(0.9, 0.9)
            )
        
        # Reset search and populate list every time it's opened
        self.country_dialog.content.children[1].text = '' # Clear search input
        self.update_country_list(self.all_countries)
        self.country_dialog.open()

    def update_country_list(self, countries_list):
        """Populates the RecycleView with a list of countries."""
        rv = self.country_dialog.content.children[0]
        rv.data = [
            {
                'text': f"{name} ({code})",
                'on_release': lambda name=name, code=code: self.select_country(name, code),
                'size_hint_y': None,
                'height': '48dp',
                'halign': 'left',
                'valign': 'middle'
            }
            for name, code in countries_list
        ]

    def on_search_text(self, instance, value):
        """Filters the country list based on user input."""
        filtered_countries = self.app.country_service.search_countries(value)
        self.update_country_list(filtered_countries)

    def select_country(self, name, code):
        """Handles the selection of a country from the dialog."""
        self.ids.country_button.text = name
        # The country code is now managed by the app service
        self.country_dialog.dismiss()

    def show_error_popup(self, text):
        """Displays a generic error popup."""
        # Prevent multiple popups
        if self.error_popup and self.error_popup.content:
            self.error_popup.dismiss()

        content = BoxLayout(orientation='vertical', spacing='10dp', padding='10dp')
        content.add_widget(Label(text=text, halign='center', color=(0, 0, 0, 1)))
        ok_button = Button(text="OK", size_hint_y=None, height='44dp')
        content.add_widget(ok_button)

        self.error_popup = Popup(title="Error", content=content, size_hint=(0.8, 0.4))
        ok_button.bind(on_release=self.error_popup.dismiss)
        self.error_popup.open()

    # This method needs to be added to the app class, not here.
    # I will move it.
    def get_country_code(self, country_name: str):
        """Gets the phone code for a given country name from the service."""
        return self.app.country_service.get_country_code(country_name)
