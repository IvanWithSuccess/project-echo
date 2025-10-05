from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.datatables import MDDataTable
from kivy.metrics import dp

class AccountsPanel(MDBoxLayout):
    """A panel that displays a table of accounts and provides management options."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # on_kv_post is a more reliable method to call after the UI is built
        self.on_kv_post = self.create_accounts_table

    def create_accounts_table(self, *args):
        """Creates and populates the MDDataTable widget."""
        # Define the table with rows and columns
        self.data_table = MDDataTable(
            size_hint=(1, 1),
            use_pagination=True,
            column_data=[
                ("Phone", dp(30)),
                ("Status", dp(20)),
                ("Tags", dp(30)),
                ("Description", dp(40)),
            ],
            row_data=[
                ("+1234567890", "Active", "[Test, VIP]", "Main test account"),
                ("+0987654321", "Inactive", "[New]", "Secondary account"),
                # Add more sample rows as needed
            ]
        )

        # Add the created table to the container defined in the KV file
        self.ids.table_container.add_widget(self.data_table)

    def show_add_account_dialog(self):
        """Placeholder for the 'Add Account' functionality."""
        print("Action: Show 'Add Account' dialog.")
        # Later, this will open a MDDialog for adding an account
