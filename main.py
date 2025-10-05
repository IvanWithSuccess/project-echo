
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivymd.app import MDApp
from kivymd.uix.tab import MDTabsBase
from kivymd.uix.floatlayout import MDFloatLayout

# --- Import the custom screen ---
from project_echo.screens.accounts_screen import AccountsPanel

# --- Load the KV files ---
# The main layout for the app
Builder.load_string("""
MDBoxLayout:
    orientation: "vertical"

    MDTopAppBar:
        title: "Project Echo"

    MDTabs:
        id: tabs
        on_tab_switch: app.on_tab_switch(*args)

<Tab>:
    # This is the base class for the content of each tab.
    # We'll add content to it dynamically.
    pass
""")

# The specific layout for the Accounts screen
Builder.load_file("project_echo/screens/accounts_screen.kv")


# =========================================================================
# >> WIDGETS AND LAYOUTS
# =========================================================================

class Tab(MDFloatLayout, MDTabsBase):
    """Class for a tab in the MDTabs widget."""
    pass

# =========================================================================
# >> MAIN APP CLASS
# =========================================================================

class ProjectEchoApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"
        # The root widget is now defined in the loaded KV string
        return Builder.load_string("""
MDBoxLayout:
    orientation: "vertical"

    MDTopAppBar:
        title: "Project Echo"

    MDTabs:
        id: tabs
        on_tab_switch: app.on_tab_switch(*args)
""")

    def on_start(self):
        """Populate the tabs with their respective content."""
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
