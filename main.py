
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.utils import get_color_from_hex
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
# --- FIX: Import the correct button class for KivyMD 1.2.0 ---
from kivymd.uix.button import MDTextButton
from kivymd.uix.label import MDLabel
from functools import partial

# Import our custom screen content
from project_echo.screens.accounts_screen import AccountsPanel

# Load KV files
Builder.load_file("project_echo/screens/accounts_screen.kv")

# --- FIX: Inherit from MDTextButton instead of the non-existent MDButton ---
class NavButton(MDTextButton):
    pass

# =========================================================================
# >> MAIN APP CLASS
# ==========================================================================

class ProjectEchoApp(MDApp):
    """The main application class with a custom side navigation."""

    def build(self):
        """Initializes the application and returns the root widget."""
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Custom"
        self.theme_cls.primary_hue = "500"
        self.theme_cls.colors["Custom"] = {
            "500": get_color_from_hex("#a58d78"),
        }

        Window.maximize()
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

        self.root.ids.screen_manager.current = 'dashboard'

    def switch_screen(self, screen_name, *args):
        """Callback function to switch the currently displayed screen."""
        self.root.ids.screen_manager.current = screen_name

# ==========================================================================
# >> MAIN EXECUTION
# ==========================================================================

if __name__ == '__main__':
    ProjectEchoApp().run()
