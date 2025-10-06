import os
import asyncio
import threading
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from functools import partial
from kivy.properties import StringProperty, ObjectProperty
from kivy.uix.boxlayout import BoxLayout

# 1. Import all Python screen classes.
from project_echo.screens.accounts_screen import AccountsPanel
from project_echo.screens.login_screen import LoginScreen
from project_echo.screens.code_verification_screen import CodeVerificationScreen
from project_echo.screens.password_verification_screen import PasswordVerificationScreen
# Import the new campaigns screen that will be created
from project_echo.screens.campaigns_screen import CampaignsScreen
from project_echo.services.telegram_service import TelegramService
from project_echo.services.country_service import CountryService


class ProjectEchoApp(App):
    """
    Main application class.
    """
    # Properties to share data between screens
    phone_to_verify = StringProperty(None)
    phone_code_hash = StringProperty(None)
    session_string_for_password = StringProperty(None)
    telegram_service = ObjectProperty(None)
    country_service = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.telegram_service = TelegramService()
        self.country_service = CountryService()

    def build(self):
        """
        Initializes the application and returns the root widget.
        """
        Window.size = (1200, 800)
        # Load KV files for each screen
        Builder.load_file('project_echo/screens/accounts_screen.kv')
        Builder.load_file('project_echo/screens/login_screen.kv')
        Builder.load_file('project_echo/screens/code_verification_screen.kv')
        Builder.load_file('project_echo/screens/password_verification_screen.kv')
        Builder.load_file('project_echo/screens/campaigns_screen.kv') # Load the new KV file
        
        return Builder.load_file('main.kv')

    def on_start(self):
        """
        Called after the build() method is finished.
        """
        self.switch_panel('accounts')

    # --- Navigation and Screen Management ---

    def switch_panel(self, panel_name):
        """Switches the view in the main content panel."""
        if panel_name == 'accounts':
            self.load_accounts()
        self.root.ids.screen_manager.current = panel_name

    def go_to_login(self, *args):
        """Called when 'Add Account' is pressed."""
        self.root.ids.screen_manager.current = 'login'

    # --- Country Service Helper ---
    def get_country_code(self, country_name: str):
        """Gets the phone code for a given country name from the service."""
        return self.country_service.get_country_code(country_name)

    # --- Asynchronous Operations ---

    def run_async(self, coro):
        """
        Runs an asynchronous task in a separate thread to avoid blocking the UI.
        """
        threading.Thread(target=asyncio.run, args=(coro,)).start()

    # --- Session and Account Management ---

    def save_session(self, phone, session_string):
        """
        Saves the new session, reloads accounts, and switches to the accounts screen.
        """
        print(f"Successfully signed in for {phone}. Session string saved.")
        self.load_accounts()
        self.root.ids.screen_manager.current = 'accounts'

    def load_accounts(self):
        """
        Loads saved Telegram account sessions and displays them.
        """
        self.root.ids.accounts_panel.load_accounts()

if __name__ == '__main__':
    ProjectEchoApp().run()
