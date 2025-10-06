
from kivy.lang import Builder
from kivy.core.window import Window
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.label import MDLabel
from functools import partial
from kivy.properties import StringProperty

from kivymd.uix.boxlayout import MDBoxLayout
from kivy.uix.behaviors import ButtonBehavior

# Import our custom screen content
from project_echo.screens.accounts_screen import AccountsPanel
# FIX: Import the new LoginScreen
from project_echo.screens.login_screen import LoginScreen

# Load KV files
Builder.load_file("project_echo/screens/accounts_screen.kv")
# FIX: Load the new login_screen.kv file
Builder.load_file("project_echo/screens/login_screen.kv")


class NavButton(ButtonBehavior, MDBoxLayout):
    text = StringProperty("")
    icon = StringProperty("")

# =========================================================================
# >> MAIN APP CLASS
# ==========================================================================

class ProjectEchoApp(MDApp):
    """The main application class with a custom side navigation."""

    def build(self):
        """Initializes the application and returns the root widget."""
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Gray"
        Window.maximize()
        return Builder.load_file('main.kv')

    def on_start(self):
        """Create and populate screens and navigation buttons."""
        screens_data = {
            "dashboard": {"icon": "view-dashboard", "title": "Dashboard"},
            "accounts": {"icon": "account-group", "title": "Accounts"},
            "campaigns": {"icon": "bullhorn", "title": "Campaigns"},
        }

        # Add main navigation screens
        for screen_name, screen_info in screens_data.items():
            screen = MDScreen(name=screen_name)
            if screen_name == "accounts":
                screen.add_widget(AccountsPanel())
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
            
        # FIX: Add the LoginScreen to the ScreenManager
        self.root.ids.screen_manager.add_widget(LoginScreen())

        # Set the default screen
        self.root.ids.screen_manager.current = 'dashboard'

    def switch_screen(self, screen_name, *args):
        """Callback function to switch the currently displayed screen."""
        self.root.ids.screen_manager.current = screen_name

# ==========================================================================
# >> MAIN EXECUTION
# ==========================================================================

if __name__ == '__main__':
    ProjectEchoApp().run()
