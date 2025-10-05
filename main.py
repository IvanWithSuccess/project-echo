
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivymd.app import MDApp
from kivymd.uix.tab import MDTabsBase
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.menu import MDDropdownMenu
from kivymd.icon_definitions import md_icons

# =========================================================================
# >> KIVY LANG DEFINITION FOR TABS
# =========================================================================
# Using Builder is a Kivy best practice for defining UI structure.
KV = """
MDBoxLayout:
    orientation: "vertical"

    MDTopAppBar:
        title: "Project Echo"

    MDTabs:
        id: tabs
        on_tab_switch: app.on_tab_switch(*args)

<Tab>:
    # This is the content for each tab.
    # We will populate it from the Python code.
    pass
"""

# =========================================================================
# >> WIDGETS AND LAYOUTS
# =========================================================================

class Tab(MDFloatLayout, MDTabsBase):
    """Class for a tab in the MDTabs widget."""
    pass

class AccountsPanel(BoxLayout):
    """
    Content for the 'Accounts' tab, now built with KivyMD components.
    This will be dynamically added to the 'Accounts' Tab.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = [20, 20, 20, 20]
        self.spacing = 20

        # --- Toolbar ---
        toolbar = BoxLayout(size_hint_y=None, height=48, spacing=10)

        # 'Create Account' Button with Icon
        create_button = Builder.load_string("""
MDFillRoundFlatButton:
    text: "CREATE ACCOUNT"
    icon: "plus"
    pos_hint: {"center_y": 0.5}
""")
        toolbar.add_widget(create_button)

        # Spacer
        toolbar.add_widget(BoxLayout())

        # Status Filter Dropdown
        self.menu_button = Builder.load_string("""
MDFlatButton:
    text: "ANY STATUS"
    pos_hint: {"center_y": 0.5}
    on_release: app.open_status_menu(self)
""")
        toolbar.add_widget(self.menu_button)
        self.add_widget(toolbar)

        # --- Data Table Placeholder ---
        table_placeholder = Builder.load_string("""
MDLabel:
    text: "Accounts data table will be here"
    halign: "center"
""")
        self.add_widget(table_placeholder)


# =========================================================================
# >> MAIN APP CLASS
# =========================================================================

class ProjectEchoApp(MDApp):
    def build(self):
        # Set the theme and style for the app
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"
        # Load the UI structure from the KV string
        return Builder.load_string(KV)

    def on_start(self):
        """
        Called after the build() method, this is where we will
        populate the tabs and create the status filter menu.
        """
        # --- Create Tabs ---
        tabs_data = {
            "Accounts": "account-group",
            "Dashboard": "view-dashboard",
            "Campaigns": "bullhorn",
        }
        for tab_name, icon_name in tabs_data.items():
            tab = Tab(title=tab_name, icon=icon_name)
            if tab_name == "Accounts":
                # Add the specific layout for the Accounts tab
                tab.add_widget(AccountsPanel())
            else:
                tab.add_widget(Builder.load_string(f"""
MDLabel:
    text: "{tab_name} content will be here"
    halign: "center"
"""))
            self.root.ids.tabs.add_widget(tab)
        
        # --- Create Status Filter Menu ---
        menu_items = [
            {"text": "Any Status", "on_release": lambda x="Any Status": self.set_status(x)},
            {"text": "Active", "on_release": lambda x="Active": self.set_status(x)},
            {"text": "Inactive", "on_release": lambda x="Inactive": self.set_status(x)},
        ]
        self.status_menu = MDDropdownMenu(
            caller=self.root.ids.tabs.get_tab_list()[0].children[0].children[1].children[0], # Bit complex, but gets the button
            items=menu_items,
            width_mult=4,
        )

    def on_tab_switch(self, instance_tabs, instance_tab, instance_tab_label, tab_text):
        """Called when a tab is switched."""
        # This is where we can load data for the specific tab
        pass

    def open_status_menu(self, button):
        """Opens the status filter dropdown menu."""
        # The caller needs to be updated each time, in case the window is resized
        self.status_menu.caller = button
        self.status_menu.open()

    def set_status(self, text_item):
        """Sets the text of the status button and closes the menu."""
        button = self.status_menu.caller
        button.text = text_item
        self.status_menu.dismiss()


# =========================================================================
# >> MAIN EXECUTION
# =========================================================================

if __name__ == '__main__':
    ProjectEchoApp().run()
