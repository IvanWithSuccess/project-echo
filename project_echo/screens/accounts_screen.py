import os
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button

class AccountsPanel(BoxLayout):
    """A panel to display and manage user accounts using standard Kivy widgets."""

    def populate_accounts(self):
        """
        Scans the root directory for .session files and populates the list.
        This method is called from the main app to ensure the list is always fresh.
        """
        # Ensure the target widget exists before proceeding
        if not self.ids.get('accounts_list'):
            return
            
        self.ids.accounts_list.clear_widgets()

        # Correctly determine the project root to find session files
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        found_accounts = False
        try:
            for filename in os.listdir(project_root):
                if filename.endswith(".session"):
                    phone_number = os.path.splitext(filename)[0]
                    
                    # Use a standard Kivy Button to represent the account
                    account_item = Button(
                        text=phone_number,
                        size_hint_y=None,
                        height='48dp'
                    )
                    self.ids.accounts_list.add_widget(account_item)
                    found_accounts = True
        except FileNotFoundError:
            # This might happen if the directory doesn't exist, though unlikely
            pass

        # If no .session files were found, display a message
        if not found_accounts:
            self.ids.accounts_list.add_widget(
                Label(
                    text="No accounts found. Add one!",
                    halign="center",
                    color=(0.5, 0.5, 0.5, 1) # A grayish color for secondary text
                )
            )
