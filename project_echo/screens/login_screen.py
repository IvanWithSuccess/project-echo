from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.app import App
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.recycleview import RecycleView
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.properties import StringProperty
from kivy.lang import Builder

# Define and style custom widgets for the popup and its list items
# This ensures the country selection popup is clean, white, and user-friendly.
Builder.load_string('''
<CountryListItem>:
    size_hint_y: None
    height: '48dp'
    background_color: (1, 1, 1, 1)
    color: (0, 0, 0, 1)
    text_size: self.width - dp(20), self.height
    halign: 'left'
    valign: 'middle'
    padding_x: '10dp'
    canvas.after:
        Color:
            rgba: 0.9, 0.9, 0.9, 1
        Line:
            points: self.x, self.y, self.x + self.width, self.y

<CountryDialogPopup>:
    title: "Choose a Country"
    size_hint: 0.8, 0.9
    BoxLayout:
        orientation: 'vertical'
        padding: '10dp'
        spacing: '10dp'
        canvas.before:
            Color:
                rgba: (1, 1, 1, 1)
            Rectangle:
                pos: self.pos
                size: self.size
        TextInput:
            id: search_bar
            hint_text: "Search for a country..."
            size_hint_y: None
            height: '48dp'
            multiline: False
            on_text: root.filter_countries(self.text)
        RecycleView:
            id: rv
            viewclass: 'CountryListItem'
            RecycleBoxLayout:
                default_size: None, dp(48)
                default_size_hint: 1, None
                size_hint_y: None
                height: self.minimum_height
                orientation: 'vertical'
''')

class CountryListItem(Button):
    pass

class CountryDialogPopup(Popup):
    """A styled popup for country selection with a search feature."""
    def __init__(self, login_screen, countries, **kwargs):
        super().__init__(**kwargs)
        self.login_screen = login_screen
        self.all_countries = countries
        self.filter_countries("")

    def filter_countries(self, search_text):
        """Filters the RecycleView data based on the search text."""
        search_text = search_text.lower()
        if not search_text:
            countries_to_display = self.all_countries
        else:
            countries_to_display = [
                (name, code) for name, code in self.all_countries
                if search_text in name.lower() or search_text in code.lower()
            ]
        
        self.ids.rv.data = [
            {'text': f"{name} ({code})", 'on_release': lambda name=name, code=code: self.select_country_and_dismiss(name, code)}
            for name, code in countries_to_display
        ]
    
    def select_country_and_dismiss(self, name, code):
        self.login_screen.select_country(name, code)
        self.dismiss()

class LoginScreen(Screen):
    selected_country_name = StringProperty("Choose a Country")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()
        self.error_popup = None
        self.country_dialog = None
        self.all_countries = self.app.country_service.get_all_countries()

    def on_enter(self, *args):
        self.ids.spinner.active = False
        self.selected_country_name = "Choose a Country"
        self.ids.phone_field.text = ""

    def send_code(self):
        country_name = self.selected_country_name
        phone_number = self.ids.phone_field.text

        if country_name == "Choose a Country" or not phone_number:
            self.show_error_popup("Please select a country and enter a phone number.")
            return

        country_code = self.app.country_service.get_country_code(country_name)
        if not country_code:
            self.show_error_popup("Invalid country selected.")
            return

        full_phone = f"{country_code}{phone_number.lstrip('0')}"
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
            self.app.session_string_for_password = result.get("session_string")
            if result.get("password_required"):
                self.app.switch_screen('password_verification_screen')
            else:
                self.app.switch_screen('code_verification_screen')
        else:
            self.show_error_popup(result.get("error", "An unknown error occurred."))

    def open_country_popup(self):
        if not self.country_dialog:
            self.country_dialog = CountryDialogPopup(self, self.all_countries)
        self.country_dialog.open()

    def select_country(self, country_name, country_code):
        self.selected_country_name = country_name
        if self.country_dialog:
            self.country_dialog.dismiss()

    def show_error_popup(self, text):
        if hasattr(self, 'error_popup') and self.error_popup:
            self.error_popup.dismiss()

        content = BoxLayout(orientation='vertical', spacing='10dp', padding='10dp')
        content.add_widget(Label(text=text, color=(0,0,0,1)))
        ok_button = Button(text="OK", size_hint_y=None, height='44dp')
        content.add_widget(ok_button)

        self.error_popup = Popup(title="Login Error", content=content, size_hint=(0.8, 0.3))
        ok_button.bind(on_release=self.error_popup.dismiss)
        self.error_popup.open()
