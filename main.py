
from kivy.lang import Builder
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
    """ Class for the content of a single tab. KivyMD 1.2.0 uses the
        MDTabsBase mixin to link this content to a tab button. """
    pass


# =========================================================================
# >> MAIN APP CLASS
# =========================================================================

class ProjectEchoApp(MDApp):
    """The main application class."""

    def build(self):
        """Initializes the application and returns the root widget.
           The root widget is defined in 'main.kv'."""
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"
        return Builder.load_file('main.kv')

    def on_start(self):
        """Populate the tabs with their respective content after the app starts."""
        tabs_data = {
            "Accounts": "account-group",
            "Dashboard": "view-dashboard",
            "Campaigns": "bullhorn",
        }

        for title, icon in tabs_data.items():
            # Create an instance of our Tab content class
            tab_content = Tab(title=title, icon=icon)

            # Add the appropriate content widget to the tab
            if title == "Accounts":
                tab_content.add_widget(AccountsPanel())
            else:
                tab_content.add_widget(MDLabel(
                    text=f"{title} content will be here",
                    halign="center"
                ))

            # Add the tab content to the main MDTabs widget
            self.root.ids.tabs.add_widget(tab_content)


# ==========================================================================
# >> MAIN EXECUTION
# ==========================================================================

if __name__ == '__main__':
    ProjectEchoApp().run()
