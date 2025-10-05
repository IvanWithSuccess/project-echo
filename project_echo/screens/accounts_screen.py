from kivy.lang import Builder
from kivy.metrics import dp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.textfield import MDTextField
# FIX: Import list components
from kivymd.uix.list import ThreeLineAvatarIconListItem, IconLeftWidget

# KV string for the dialog content is still needed
Builder.load_string("""
<DialogContent>:
    orientation: "vertical"
    spacing: "12dp"
    size_hint_y: None
    height: "180dp"

    MDTextField:
        id: phone_field
        hint_text: "Phone Number"

    MDTextField:
        id: tags_field
        hint_text: "Tags"

    MDTextField:
        id: description_field
        hint_text: "Description"
"""
)

class DialogContent(MDBoxLayout):
    """Content widget for the 'Add Account' dialog."""
    pass

class AccountsPanel(MDBoxLayout):
    """A panel that displays a list of accounts and provides management options."""
    
    speed_dial_data = {
        'cloud-upload-outline': 'Import from API',
        'pencil': 'Add manually',
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.dialog = None

    def speed_dial_callback(self, instance):
        icon = instance.icon
        if icon == 'pencil':
            self.show_add_account_dialog()
        elif icon == 'cloud-upload-outline':
            print("Action: Show 'API Import' dialog (not implemented yet).")

    def show_add_account_dialog(self):
        """Creates and shows a new 'Add Account' dialog."""
        self.dialog = MDDialog(
            title="Add New Account",
            type="custom",
            content_cls=DialogContent(),
            buttons=[
                MDFlatButton(text="CANCEL", on_release=self.close_dialog),
                MDRaisedButton(text="ADD", on_release=self.add_account),
            ],
        )
        self.dialog.open()

    def close_dialog(self, *args):
        if self.dialog:
            self.dialog.dismiss()
            self.dialog = None

    # FIX: Rewritten to add items to the MDList
    def add_account(self, *args):
        if not self.dialog:
            return

        content = self.dialog.content_cls
        phone = content.ids.phone_field.text
        tags = content.ids.tags_field.text
        description = content.ids.description_field.text

        if phone:
            # Create a new list item
            list_item = ThreeLineAvatarIconListItem(
                IconLeftWidget(
                    icon="account-circle-outline"
                ),
                text=f"Phone: {phone}",
                secondary_text=f"Tags: {tags}",
                tertiary_text=f"Description: {description}",
            )
            # Add the new item to the list
            self.ids.account_list.add_widget(list_item)
        
        self.close_dialog()
