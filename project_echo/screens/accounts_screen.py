import os
from kivy.lang import Builder
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.list import OneLineIconListItem, IconLeftWidget

# FIX: Removed Builder call. All KV files will be loaded centrally in main.py
# for better stability and predictable loading order.

class AccountsPanel(MDBoxLayout):
    """A panel to display and manage user accounts."""

    def populate_accounts(self):
        """
        Scans the root directory for .session files and populates the list.
        This method is called from the main app to ensure the list is always fresh.
        """
        if not self.ids.get('accounts_list'):
            return
            
        self.ids.accounts_list.clear_widgets()

        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        found_accounts = False
        try:
            for filename in os.listdir(project_root):
                if filename.endswith(".session"):
                    phone_number = os.path.splitext(filename)[0]
                    
                    account_item = OneLineIconListItem(text=phone_number)
                    icon = IconLeftWidget(icon="account-circle")
                    account_item.add_widget(icon)
                    self.ids.accounts_list.add_widget(account_item)
                    found_accounts = True
        except FileNotFoundError:
            pass

        if not found_accounts:
            self.ids.accounts_list.add_widget(
                MDLabel(
                    text="No accounts found. Add one!",
                    halign="center",
                    theme_text_color="Secondary"
                )
            )
