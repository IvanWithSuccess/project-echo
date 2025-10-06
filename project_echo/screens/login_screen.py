import asyncio
from functools import partial

from kivy.lang import Builder
from kivy.clock import Clock
from kivy.properties import ObjectProperty
from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivymd.uix.list import OneLineListItem
from kivymd.uix.screen import MDScreen
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.textfield import MDTextField
from kivymd.uix.boxlayout import MDBoxLayout

# FIX: Removed Builder call. All KV files will be loaded centrally in main.py

class LoginScreen(MDScreen):
    """The login screen, completely refactored to be asynchronous and more user-friendly."""

    country_dialog = ObjectProperty(None)

    def on_pre_enter(self, *args):
        """Initialize services and bind listeners."""
        self.app = MDApp.get_running_app()
        self.ids.phone_field.bind(text=self.sync_country_from_phone)

    def open_country_dialog(self):
        """Opens a searchable dialog for country selection."""
        if not self.country_dialog:
            search_field = MDTextField(
                hint_text="Search country...",
                mode="fill",
                on_text_validate=self._filter_countries,
            )
            search_field.bind(text=self._filter_countries)
            
            self.country_list = MDBoxLayout(orientation='vertical', adaptive_height=True)
            scroll = MDScrollView()
            scroll.add_widget(self.country_list)

            self.country_dialog = MDDialog(
                title="Choose a Country",
                type="custom",
                content_cls=MDBoxLayout(
                    search_field, scroll, orientation="vertical", spacing="12dp", size_hint_y=None, height="400dp"
                ),
            )
        self._filter_countries(search_field) # Populate with all countries initially
        self.country_dialog.open()

    def _filter_countries(self, search_field, text=""):
        """Filters the country list based on user input in the search field."""
        self.country_list.clear_widgets()
        countries = self.app.country_service.find_countries(search_field.text)
        for country_name in countries:
            code = self.app.country_service.get_code_by_country(country_name)
            item = OneLineListItem(
                text=f"{country_name} ({code})",
                on_release=partial(self.set_country, country_name, code)
            )
            self.country_list.add_widget(item)

    def set_country(self, country_name, country_code, *args):
        """Updates the UI with the selected country."""
        self.ids.country_field.text = country_name
        self.ids.phone_field.text = country_code
        self.country_dialog.dismiss()

    def sync_country_from_phone(self, instance, phone_code):
        """Updates the country field based on the manually entered phone code."""
        if self.app.country_service.get_code_by_country(self.ids.country_field.text) == phone_code:
            return
        
        country = self.app.country_service.get_country_by_code(phone_code)
        if country:
            self.ids.country_field.text = country

    def on_next_button_press(self):
        """Starts the asynchronous login process."""
        asyncio.create_task(self.send_code_async())

    async def send_code_async(self):
        """The async part of the login process. Calls the telegram service."""
        self.ids.spinner.active = True
        phone = self.ids.phone_field.text
        
        result = await self.app.telegram_service.send_code(phone)
        
        self.ids.spinner.active = False
        if result["success"]:
            self.app.phone_to_verify = phone
            self.manager.current = 'code_verification_screen'
        else:
            self.show_dialog("Login Error", result.get("error", "An unknown error occurred."))

    def show_dialog(self, title, text):
        """Helper to show a simple dialog."""
        if not hasattr(self, 'dialog') or not self.dialog:
            self.dialog = MDDialog(
                title=title,
                text=text,
                buttons=[MDFlatButton(text="OK", on_release=lambda *args: self.dialog.dismiss())],
            )
        else:
            self.dialog.title = title
            self.dialog.text = text
        self.dialog.open()
