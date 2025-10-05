
from kivy.lang import Builder
from kivy.core.window import Window
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.label import MDLabel
from functools import partial
from kivy.uix.screenmanager import NoTransition
from kivy.properties import StringProperty

# --- FIX: Import the correct base classes for a custom clickable layout ---
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.uix.behaviors import ButtonBehavior
from kivymd.uix.behaviors import CircularRippleBehavior

# Import our custom screen content
from project_echo.screens.accounts_screen import AccountsPanel

# Load KV files
Builder.load_file("project_echo/screens/accounts_screen.kv")

# --- FIX: Define NavButton as a clickable layout with ripple effect ---
class NavButton(MDBoxLayout, ButtonBehavior, CircularRippleBehavior):
    # Add properties for both text and icon so they can be set from Python
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
        self.root.ids.screen_manager.transition = NoTransition()

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

            # This now correctly creates an instance of our custom layout button
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
