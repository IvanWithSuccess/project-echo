
from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.tab import MDTabsBase
from kivymd.uix.floatlayout import MDFloatLayout

# --- Import the custom screen ---
from project_echo.screens.accounts_screen import AccountsPanel

# --- Load the KV file for the Accounts screen ---
# This will be automatically associated with the AccountsPanel class by Kivy
Builder.load_file("project_echo/screens/accounts_screen.kv")


# =========================================================================
# >> WIDGETS AND LAYOUTS
# =========================================================================

class Tab(MDFloatLayout, MDTabsBase):
    """Base class for a tab in the MDTabs widget."""
    pass

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
        on_tab_switch: app.on_tab_switch(*args)
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
            tab = Tab(title=tab_name, icon=icon_name)
            if tab_name == "Accounts":
                # Create an instance of the AccountsPanel from the separate file
                tab.add_widget(AccountsPanel())
            else:
                # Add a placeholder for other tabs
                tab.add_widget(Builder.load_string(f'''MDLabel:
    text: "{tab_name} content will be here"
    halign: "center"'''))
            self.root.ids.tabs.add_widget(tab)

    def on_tab_switch(self, *args):
        """Called when a tab is switched. Can be used to load data."""
        pass

# ==========================================================================
# >> MAIN EXECUTION
# ==========================================================================

if __name__ == '__main__':
    ProjectEchoApp().run()
