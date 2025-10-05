from kivy.lang import Builder
from kivy.metrics import dp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.datatables import MDDataTable
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.textfield import MDTextField

# KV string for the dialog content
Builder.load_string("""
<DialogContent>:
    orientation: "vertical"
    spacing: "12dp"
    size_hint_y: None
    height: "180dp"

    MDTextField:
        id: phone_field
        hint_text: "Phone Number"
        helper_text: "e.g., +1234567890"
        helper_text_mode: "on_focus"

    MDTextField:
        id: tags_field
        hint_text: "Tags"
        helper_text: "Comma-separated, e.g., vip, test, new"
        helper_text_mode: "on_focus"

    MDTextField:
        id: description_field
        hint_text: "Description"
"""
)

class DialogContent(MDBoxLayout):
    """Content widget for the 'Add Account' dialog."""
    pass

class AccountsPanel(MDBoxLayout):
    """A panel that displays a table of accounts and provides management options."""
    
    speed_dial_data = {
        'cloud-upload-outline': 'Import from API',
        'pencil': 'Add manually',
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.dialog = None
        self.data_table = None

    def on_kv_post(self, base_widget):
        """Called after the kv file is loaded. Creates the data table."""
        self.create_accounts_table()

    def create_accounts_table(self):
        """Creates and populates the MDDataTable widget."""
        self.data_table = MDDataTable(
            size_hint=(1, 1),
            # FIX: Disabled pagination to avoid startup crash on KivyMD 1.2.0
            # use_pagination=True,
            column_data=[
                ("Phone", dp(30)),
                ("Status", dp(20)),
                ("Tags", dp(30)),
                ("Description", dp(40)),
            ],
            row_data=[]
        )
        self.ids.table_container.add_widget(self.data_table)

    def speed_dial_callback(self, instance):
        """Handle actions from the speed dial buttons."""
        icon = instance.icon
        if icon == 'pencil':
            self.show_add_account_dialog()
        elif icon == 'cloud-upload-outline':
            print("Action: Show 'API Import' dialog (not implemented yet).")

    def show_add_account_dialog(self):
        """Creates and shows a new 'Add Account' dialog every time to prevent state issues."""
        self.dialog = MDDialog(
            title="Add New Account",
            type="custom",
            content_cls=DialogContent(),
            buttons=[
                MDFlatButton(
                    text="CANCEL",
                    on_release=self.close_dialog
                ),
                MDRaisedButton(
                    text="ADD",
                    on_release=self.add_account
                ),
            ],
        )
        self.dialog.open()

    def close_dialog(self, *args):
        """Closes the currently active dialog."""
        if self.dialog:
            self.dialog.dismiss()
            self.dialog = None

    def add_account(self, *args):
        """Adds the new account data from the currently active dialog."""
        if not self.dialog:
            return

        content = self.dialog.content_cls
        phone = content.ids.phone_field.text
        tags = content.ids.tags_field.text
        description = content.ids.description_field.text

        if phone and self.data_table:
            self.data_table.add_row((phone, "New", f"[{tags}]", description))
        
        self.close_dialog()
