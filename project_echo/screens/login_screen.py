import asyncio
from functools import partial

from kivy.lang import Builder
from kivy.properties import ObjectProperty
from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivymd.uix.list import OneLineListItem
from kivymd.uix.screen import MDScreen
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.textfield import MDTextField
from kivymd.uix.boxlayout import MDBoxLayout


class LoginScreen(MDScreen):
    """The login screen, completely refactored to be asynchronous and more user-friendly."""

    country_dialog = ObjectProperty(None)
    search_field = ObjectProperty(None)
    country_list = ObjectProperty(None)

    def on_pre_enter(self, *args):
        """Initialize services and bind listeners."""
        self.app = MDApp.get_running_app()
        self.ids.phone_field.bind(text=self.sync_country_from_phone)

    def open_country_dialog(self):
        """
        FIX: Opens a searchable dialog for country selection.
        This logic has been fixed to prevent the UnboundLocalError by ensuring
        the dialog and its components are created once and reused correctly.
        """
        if not self.country_dialog:
            self.search_field = MDTextField(
                hint_text="Search country...",
                mode="fill",
            )
            self.search_field.bind(text=self._filter_countries)

            self.country_list = MDBoxLayout(orientation='vertical', adaptive_height=True)
            scroll = MDScrollView()
            scroll.add_widget(self.country_list)

            content_layout = MDBoxLayout(
                self.search_field, scroll, orientation="vertical", spacing="12dp", size_hint_y=None, height="400dp"
            )

            self.country_dialog = MDDialog(
                title="Choose a Country",
                type="custom",
                content_cls=content_layout,
            )
        
        # Always clear the search field and repopulate the list when opening
        self.search_field.text = ""
        self._filter_countries(self.search_field)
        self.country_dialog.open()

    def _filter_countries(self, instance, text=""):
        """Filters the country list based on user input in the search field."""
        self.country_list.clear_widgets()
        countries = self.app.country_service.find_countries(instance.text)
        if not countries:
            self.country_list.add_widget(OneLineListItem(text="No countries found"))

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
        if self.country_dialog:
            self.country_dialog.dismiss()

    def sync_country_from_phone(self, instance, phone_code):
        """Updates the country field based on the manually entered phone code."""
        current_code = self.app.country_service.get_code_by_country(self.ids.country_field.text)
        if current_code == phone_code:
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
