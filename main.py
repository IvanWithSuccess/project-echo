
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
# FIX: Import the missing PasswordVerificationScreen class
from project_echo.screens.password_verification_screen import PasswordVerificationScreen
from project_echo.services.telegram_service import TelegramService
from project_echo.services.country_service import CountryService

# 2. Now, load the KV files.
Builder.load_file("project_echo/screens/accounts_screen.kv")
Builder.load_file("project_echo/screens/login_screen.kv")
Builder.load_file("project_echo/screens/code_verification_screen.kv")
# FIX: Load the missing KV file for the password screen
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
    accounts_panel_widget = ObjectProperty(None) # To hold the instance

    def build(self):
        """Initializes the application and returns the root widget."""
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Gray"
        Window.maximize()
        self.telegram_service = TelegramService()
        self.country_service = CountryService()
        return Builder.load_file('main.kv')

    def on_start(self):
        """Create and populate screens and navigation buttons."""
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
            
        # Add all login-flow screens to the ScreenManager
        self.root.ids.screen_manager.add_widget(LoginScreen(name='login_screen'))
        self.root.ids.screen_manager.add_widget(CodeVerificationScreen(name='code_verification_screen'))
        # FIX: Add the password verification screen to the manager
        self.root.ids.screen_manager.add_widget(PasswordVerificationScreen(name='password_verification_screen'))

        self.root.ids.screen_manager.current = 'dashboard'

    def switch_screen(self, screen_name, *args):
        """Callback function to switch the currently displayed screen."""
        self.root.ids.screen_manager.current = screen_name
        if screen_name == "accounts":
            if self.accounts_panel_widget:
                self.accounts_panel_widget.populate_accounts()

    def go_to_login(self, *args):
        """Switches to the login screen."""
        self.switch_screen('login_screen')

# ==========================================================================
# >> MAIN EXECUTION
# ==========================================================================

if __name__ == '__main__':
    ProjectEchoApp().run()
