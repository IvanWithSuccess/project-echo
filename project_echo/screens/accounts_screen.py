
from kivy.uix.boxlayout import BoxLayout
from kivymd.app import MDApp
from kivymd.uix.menu import MDDropdownMenu

class AccountsPanel(BoxLayout):
    """
    Content for the 'Accounts' tab. The UI for this widget is defined
    in the corresponding `accounts_screen.kv` file.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.menu = None # To hold the MDDropdownMenu instance

    def on_kv_post(self, base_widget):
        """
        This Kivy method is called after the .kv file has been loaded.
        It's the perfect place to create the dropdown menu.
        """
        menu_items = [
            {"text": "Any Status", "on_release": lambda x="Any Status": self.set_status(x)},
            {"text": "Active", "on_release": lambda x="Active": self.set_status(x)},
            {"text": "Inactive", "on_release": lambda x="Inactive": self.set_status(x)},
        ]

        self.menu = MDDropdownMenu(
            caller=self.ids.status_button,  # We can now safely access the button by its id
            items=menu_items,
            width_mult=4,
        )

    def open_status_menu(self):
        """Opens the status filter dropdown menu."""
        if self.menu:
            self.menu.open()

    def set_status(self, text_item):
        """Sets the text of the status button and closes the menu."""
        if self.menu:
            self.ids.status_button.text = text_item
            self.menu.dismiss()
