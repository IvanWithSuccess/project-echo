
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivymd.app import MDApp
from kivymd.uix.tab import MDTabsBase
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.menu import MDDropdownMenu
from kivymd.icon_definitions import md_icons
from kivy.clock import Clock

# =========================================================================
# >> KIVY LANG DEFINITION
# =========================================================================
KV = """
MDBoxLayout:
    orientation: "vertical"

    MDTopAppBar:
        title: "Project Echo"

    MDTabs:
        id: tabs
        on_tab_switch: app.on_tab_switch(*args)
"""

# =========================================================================
# >> WIDGETS AND LAYOUTS
# =========================================================================

class Tab(MDFloatLayout, MDTabsBase):
    """Class for a tab in the MDTabs widget."""
    pass

class AccountsPanel(BoxLayout):
    """Content for the 'Accounts' tab, built with KivyMD components."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = [20, 20, 20, 20]
        self.spacing = 20

        toolbar = BoxLayout(size_hint_y=None, height=48, spacing=10)

        create_button = Builder.load_string("""
MDFillRoundFlatButton:
    text: "CREATE ACCOUNT"
    icon: "plus"
    pos_hint: {"center_y": 0.5}
""")
        toolbar.add_widget(create_button)

        toolbar.add_widget(BoxLayout())

        self.menu_button = Builder.load_string("""
MDFlatButton:
    id: status_button
    text: "ANY STATUS"
    pos_hint: {"center_y": 0.5}
    on_release: app.open_status_menu(self)
""")
        toolbar.add_widget(self.menu_button)
        self.add_widget(toolbar)

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
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"
        return Builder.load_string(KV)

    def on_start(self):
        """
        Populate the tabs and schedule the menu creation for the next frame
        to avoid race conditions with widget creation.
        """
        tabs_data = {
            "Accounts": "account-group",
            "Dashboard": "view-dashboard",
            "Campaigns": "bullhorn",
        }
        for tab_name, icon_name in tabs_data.items():
            tab = Tab(title=tab_name, icon=icon_name)
            if tab_name == "Accounts":
                tab.add_widget(AccountsPanel())
            else:
                tab.add_widget(Builder.load_string(f'''MDLabel:
    text: "{tab_name} content will be here"
    halign: "center"'''))
            self.root.ids.tabs.add_widget(tab)
        
        Clock.schedule_once(self.create_status_menu)

    def create_status_menu(self, *args):
        """
        Creates the dropdown menu for the status filter.
        This is called after the main UI is built to ensure widgets are available.
        """
        menu_items = [
            {"text": "Any Status", "on_release": lambda x="Any Status": self.set_status(x)},
            {"text": "Active", "on_release": lambda x="Active": self.set_status(x)},
            {"text": "Inactive", "on_release": lambda x="Inactive": self.set_status(x)},
        ]
        
        # Find the button to anchor the menu. This is now safe to call.
        accounts_tab_content = self.root.ids.tabs.get_tab_list()[0].parent.parent.children[0]
        status_button = accounts_tab_content.ids.status_button

        self.status_menu = MDDropdownMenu(
            caller=status_button,
            items=menu_items,
            width_mult=4,
        )

    def on_tab_switch(self, *args):
        """Called when a tab is switched."""
        pass

    def open_status_menu(self, button):
        """Opens the status filter dropdown menu."""
        if hasattr(self, 'status_menu'):
            self.status_menu.caller = button
            self.status_menu.open()

    def set_status(self, text_item):
        """Sets the text of the status button and closes the menu."""
        if hasattr(self, 'status_menu'):
            self.status_menu.caller.text = text_item
            self.status_menu.dismiss()

# ==========================================================================
# >> MAIN EXECUTION
# ==========================================================================

if __name__ == '__main__':
    ProjectEchoApp().run()
