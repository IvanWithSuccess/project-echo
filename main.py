
from kivy.lang import Builder
from kivy.core.window import Window
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
# --- Correctly import all necessary list components ---
from kivymd.uix.list import OneLineIconListItem, IconLeftWidget
from kivymd.uix.label import MDLabel
from functools import partial

# Import our custom screen content
from project_echo.screens.accounts_screen import AccountsPanel

# Load the KV files
Builder.load_file("project_echo/screens/accounts_screen.kv")

# =========================================================================
# >> MAIN APP CLASS
# ==========================================================================

class ProjectEchoApp(MDApp):
    """The main application class with side navigation."""

    def build(self):
        """Initializes the application and returns the root widget."""
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"
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
            # --- 1. Create the screen ---
            screen = MDScreen(name=screen_name)
            if screen_name == "accounts":
                screen.add_widget(AccountsPanel())
            else:
                screen.add_widget(MDLabel(
                    text=f"{screen_info['title']} content will be here",
                    halign="center"
                ))
            self.root.ids.screen_manager.add_widget(screen)

            # --- 2. Create the navigation button (Corrected Method) ---
            nav_item = OneLineIconListItem(
                text=screen_info['title'],
                on_release=partial(self.switch_screen, screen_name)
            )
            # Create an IconLeftWidget and add it to the list item
            icon = IconLeftWidget(icon=screen_info['icon'])
            nav_item.add_widget(icon)
            self.root.ids.nav_list.add_widget(nav_item)

        # Start on the dashboard screen
        self.root.ids.screen_manager.current = 'dashboard'

    def switch_screen(self, screen_name, *args):
        """Callback function to switch the currently displayed screen."""
        self.root.ids.screen_manager.current = screen_name

# ==========================================================================
# >> MAIN EXECUTION
# ==========================================================================

if __name__ == '__main__':
    ProjectEchoApp().run()
