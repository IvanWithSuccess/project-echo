import asyncio
import threading
from functools import partial

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


class LoginScreen(MDScreen):
    """The login screen, refactored to handle asyncio in a separate thread."""

    country_dialog = ObjectProperty(None)
    search_field = ObjectProperty(None)
    country_list = ObjectProperty(None)

    def on_pre_enter(self, *args):
        self.app = MDApp.get_running_app()
        self.ids.phone_field.bind(text=self.sync_country_from_phone)

    def open_country_dialog(self):
        if not self.country_dialog:
            self.search_field = MDTextField(hint_text="Search country...", mode="fill")
            self.search_field.bind(text=self._filter_countries)
            self.country_list = MDBoxLayout(orientation='vertical', adaptive_height=True)
            scroll = MDScrollView(self.country_list)
            content_layout = MDBoxLayout(
                self.search_field, scroll, orientation="vertical", spacing="12dp", size_hint_y=None, height="400dp"
            )
            self.country_dialog = MDDialog(title="Choose a Country", type="custom", content_cls=content_layout)

        self.search_field.text = ""
        self.country_list.clear_widgets()
        self.country_list.add_widget(OneLineListItem(text="Loading..."))
        self.country_dialog.open()
        Clock.schedule_once(lambda dt: self._filter_countries(self.search_field, ""))

    def _filter_countries(self, instance, text):
        self.country_list.clear_widgets()
        countries = self.app.country_service.find_countries(text)
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
        self.ids.country_field.text = country_name
        self.ids.phone_field.text = country_code
        if self.country_dialog:
            self.country_dialog.dismiss()

    def sync_country_from_phone(self, instance, phone_code):
        country = self.app.country_service.get_country_by_code(phone_code)
        if country and self.ids.country_field.text != country:
            self.ids.country_field.text = country

    def on_next_button_press(self):
        """FIX: Runs the async operation in a separate thread."""
        self.ids.spinner.active = True
        threading.Thread(target=self.run_async_send_code, daemon=True).start()

    def run_async_send_code(self):
        """Helper that runs the asyncio event loop in the thread."""
        try:
            result = asyncio.run(self.send_code_async())
        except Exception as e:
            result = {"success": False, "error": str(e)}
        Clock.schedule_once(lambda dt: self.process_send_code_result(result))

    async def send_code_async(self):
        """The actual async logic for sending the code."""
        phone = self.ids.phone_field.text
        return await self.app.telegram_service.send_code(phone)

    def process_send_code_result(self, result):
        """Updates the UI on the main thread after the async call."""
        self.ids.spinner.active = False
        if result.get("success"):
            self.app.phone_to_verify = self.ids.phone_field.text
            self.app.phone_code_hash = result["phone_code_hash"]
            self.app.switch_screen('code_verification_screen')
        else:
            self.show_dialog("Login Error", result.get("error", "An unknown error occurred."))

    def show_dialog(self, title, text):
        if not hasattr(self, 'dialog') or not self.dialog:
            self.dialog = MDDialog(
                title=title, text=text,
                buttons=[MDFlatButton(text="OK", on_release=lambda *args: self.dialog.dismiss())]
            )
        else:
            self.dialog.title = title
            self.dialog.text = text
        self.dialog.open()
