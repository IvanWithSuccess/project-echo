
import os
import asyncio
import threading
from kivy.lang import Builder
from kivy.core.window import Window
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.label import MDLabel
from functools import partial
from kivy.properties import StringProperty, ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.behaviors import ButtonBehavior

# 1. Import all Python classes first.
from project_echo.screens.accounts_screen import AccountsPanel
from project_echo.screens.login_screen import LoginScreen
from project_echo.screens.code_verification_screen import CodeVerificationScreen
from project_echo.screens.password_verification_screen import PasswordVerificationScreen
from project_echo.services.telegram_service import TelegramService
from project_echo.services.country_service import CountryService

# 2. Now, load the KV files.
Builder.load_file("project_echo/screens/accounts_screen.kv")
Builder.load_file("project_echo/screens/login_screen.kv")
Builder.load_file("project_echo/screens/code_verification_screen.kv")
Builder.load_file("project_echo/screens/password_verification_screen.kv")


class NavButton(ButtonBehavior, BoxLayout):
    text = StringProperty("")
    icon = StringProperty("")

# =========================================================================
# >> MAIN APP CLASS
# =========================================================================

class ProjectEchoApp(MDApp):
    """The main application class with a custom side navigation."""

    phone_to_verify = StringProperty()
    phone_code_hash = StringProperty()
    session_string_for_password = StringProperty()

    telegram_service = ObjectProperty(None)
    country_service = ObjectProperty(None)
    accounts_panel_widget = ObjectProperty(None)

    # FIX: Add asyncio loop management
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever)
        self.thread.daemon = True

    def build(self):
        """Initializes the application and returns the root widget."""
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Gray"
        Window.maximize()
        self.telegram_service = TelegramService()
        self.country_service = CountryService()
        return Builder.load_file('main.kv')

    def on_start(self):
        """Start the asyncio thread and populate screens."""
        self.thread.start() # Start the asyncio event loop thread
        
        screens_data = {
            "dashboard": {"icon": "view-dashboard", "title": "Dashboard"},
            "accounts": {"icon": "account-group", "title": "Accounts"},
            "campaigns": {"icon": "bullhorn", "title": "Campaigns"},
        }

        for screen_name, screen_info in screens_data.items():
            screen = MDScreen(name=screen_name)
            if screen_name == "accounts":
                self.accounts_panel_widget = AccountsPanel()
                screen.add_widget(self.accounts_panel_widget)
            else:
                screen.add_widget(MDLabel(
                    text=f"{screen_info['title']} content here",
                    halign="center"
                ))
            self.root.ids.screen_manager.add_widget(screen)

            nav_button = NavButton(
                text=screen_info['title'],
                icon=screen_info['icon'],
                on_release=partial(self.switch_screen, screen_name)
            )
            self.root.ids.nav_list.add_widget(nav_button)
            
        self.root.ids.screen_manager.add_widget(LoginScreen(name='login_screen'))
        self.root.ids.screen_manager.add_widget(CodeVerificationScreen(name='code_verification_screen'))
        self.root.ids.screen_manager.add_widget(PasswordVerificationScreen(name='password_verification_screen'))

        self.root.ids.screen_manager.current = 'dashboard'

    def on_stop(self):
        """Stop the asyncio event loop."""
        self.loop.call_soon_threadsafe(self.loop.stop)

    # FIX: Add a helper to run async tasks from the Kivy thread
    def run_async(self, coro):
        """Helper to run a coroutine on the asyncio event loop."""
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    def switch_screen(self, screen_name, *args):
        """Callback function to switch the currently displayed screen."""
        self.root.ids.screen_manager.current = screen_name
        if screen_name == "accounts":
            if self.accounts_panel_widget:
                self.accounts_panel_widget.populate_accounts()

    def go_to_login(self, *args):
        """Switches to the login screen."""
        self.switch_screen('login_screen')

    def save_session(self, phone_number, session_string):
        """Saves the session string to a file and switches to the accounts screen."""
        filename = f"{phone_number.replace('+', '')}.session"
        project_root = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(project_root, filename)

        try:
            with open(file_path, "w") as f:
                f.write(session_string)
            print(f"Session saved successfully to {file_path}")
            self.switch_screen('accounts')
        except IOError as e:
            print(f"Error saving session file: {e}")

# ==========================================================================
# >> MAIN EXECUTION
# ==========================================================================

if __name__ == '__main__':
    ProjectEchoApp().run()
