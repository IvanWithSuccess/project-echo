
from kivy.lang import Builder
from kivymd.app import MDApp

# --- Import the custom screen and new Tab components ---
from project_echo.screens.accounts_screen import AccountsPanel
# FIX: Corrected the import path from .tabs to .tab and removed non-existent classes
from kivymd.uix.tab import MDTabs, MDTabsItem
from kivymd.uix.label import MDLabel

# --- Load the KV file for the Accounts screen ---
Builder.load_file("project_echo/screens/accounts_screen.kv")


# =========================================================================
# >> MAIN APP CLASS
# =========================================================================

class ProjectEchoApp(MDApp):
    """The main application class."""

    # Define the main KV string for the application's root widget
    KV = """
MDBoxLayout:
    orientation: "vertical"

    MDTopAppBar:
        title: "Project Echo"

    MDTabs:
        id: tabs
"""

    def build(self):
        """Initializes the application and returns the root widget."""
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"
        return Builder.load_string(self.KV)

    def on_start(self):
        """Populate the tabs with their respective content after the app starts."""
        tabs_data = {
            "Accounts": "account-group",
            "Dashboard": "view-dashboard",
            "Campaigns": "bullhorn",
        }
        for tab_name, icon_name in tabs_data.items():
            # FIX: Switched to the new KivyMD 2.0 tab creation API
            # Icon and text are now direct properties of MDTabsItem
            item = MDTabsItem(text=tab_name, icon=icon_name)

            if tab_name == "Accounts":
                item.add_widget(AccountsPanel())
            else:
                item.add_widget(MDLabel(
                    text=f"{tab_name} content will be here",
                    halign="center"
                ))
            self.root.ids.tabs.add_widget(item)


# ==========================================================================
# >> MAIN EXECUTION
# ==========================================================================

if __name__ == '__main__':
    ProjectEchoApp().run()
