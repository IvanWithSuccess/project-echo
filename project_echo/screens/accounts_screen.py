from kivy.uix.boxlayout import BoxLayout
from kivymd.uix.list import OneLineIconListItem
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton


# =========================================================================
# >> ACCOUNTS PANEL WIDGET
# =========================================================================

class AccountsPanel(BoxLayout):
    """ Widget that holds the UI for the 'Accounts' tab. """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Populate the list on initialization (example)
        self.add_account("Initial Account 1")
        self.add_account("Initial Account 2")

    def add_account(self, account_name=None):
        """ Adds a new account item to the list. 
            If account_name is None, it will show a dialog (not implemented)."""
        if account_name is None:
            # This is where you would open a dialog to get the account name
            print("Add account dialog should open here.")
            return

        # Create a new list item and add it to the MDList
        item = OneLineIconListItem(text=account_name)
        self.ids.account_list.add_widget(item)
