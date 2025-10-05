
from kivy.lang import Builder
# --- Import Kivy's Window module to control the window size ---
from kivy.core.window import Window
from kivymd.app import MDApp
from kivymd.uix.tab import MDTabsBase
from kivy.uix.floatlayout import FloatLayout
from kivymd.uix.label import MDLabel

# Import our custom screen content
from project_echo.screens.accounts_screen import AccountsPanel

# Load the KV file for the accounts screen widget
Builder.load_file("project_echo/screens/accounts_screen.kv")


# =========================================================================
# >> TAB CONTENT CLASS (KivyMD 1.2.0 Style)
# =========================================================================

class Tab(FloatLayout, MDTabsBase):
    """ Class for the content of a single tab. """
    pass


# =========================================================================
# >> MAIN APP CLASS
# =========================================================================

class ProjectEchoApp(MDApp):
    """The main application class."""

    def build(self):
        """Initializes the application and returns the root widget."""
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"
        
        # --- Maximize the window on startup ---
        Window.maximize()
        
        return Builder.load_file('main.kv')

    def on_start(self):
        """Populate the tabs with their respective content after the app starts."""
        # --- Reordered tabs as requested: Dashboard -> Accounts -> Campaigns ---
        tabs_data = {
            "Dashboard": "view-dashboard",
            "Accounts": "account-group",
            "Campaigns": "bullhorn",
        }

        for title, icon in tabs_data.items():
            tab_content = Tab(title=title, icon=icon)

            if title == "Accounts":
                tab_content.add_widget(AccountsPanel())
            else:
                # --- Use a standard font style for content labels ---
                tab_content.add_widget(MDLabel(
                    text=f"{title} content will be here",
                    halign="center",
                    font_style="Body1" 
                ))

            self.root.ids.tabs.add_widget(tab_content)


# ==========================================================================
# >> MAIN EXECUTION
# ==========================================================================

if __name__ == '__main__':
    ProjectEchoApp().run()
