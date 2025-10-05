from kivy.lang import Builder
from kivy.metrics import dp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.textfield import MDTextField
# FIX: Added missing import for OneLineIconListItem
from kivymd.uix.list import ThreeLineAvatarIconListItem, IconLeftWidget, OneLineIconListItem
from kivymd.uix.menu import MDDropdownMenu

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
    pass

class AccountsPanel(MDBoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.dialog = None
        # Menu is initialized to None
        self.menu = None

    def open_menu(self):
        """FIX: Creates the menu on the first press (lazy initialization) and opens it."""
        # Create the menu if it doesn't exist yet
        if not self.menu:
            menu_items = [
                {
                    "viewclass": "OneLineIconListItem",
                    "text": "Add manually",
                    "height": dp(56),
                    "on_release": self.show_add_account_dialog,
                    "left_icon": "pencil"  # Correct property for icon
                },
                {
                    "viewclass": "OneLineIconListItem",
                    "text": "Import from API",
                    "height": dp(56),
                    "on_release": self.show_api_import_dialog,
                    "left_icon": "cloud-upload-outline" # Correct property for icon
                }
            ]
            self.menu = MDDropdownMenu(
                caller=self.ids.add_button,
                items=menu_items,
                width_mult=4,
            )
        self.menu.open()

    def show_add_account_dialog(self):
        """Creates and shows a new 'Add Account' dialog."""
        if self.menu: 
            self.menu.dismiss()
            
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
    
    def show_api_import_dialog(self):
        """Placeholder for the API import dialog."""
        if self.menu: 
            self.menu.dismiss()
        print("Action: Show 'API Import' dialog (not implemented yet).")

    def close_dialog(self, *args):
        if self.dialog:
            self.dialog.dismiss()
            self.dialog = None

    def add_account(self, *args):
        if not self.dialog:
            return

        content = self.dialog.content_cls
        phone = content.ids.phone_field.text
        tags = content.ids.tags_field.text
        description = content.ids.description_field.text

        if phone:
            list_item = ThreeLineAvatarIconListItem(
                IconLeftWidget(icon="account-circle-outline"),
                text=f"Phone: {phone}",
                secondary_text=f"Tags: {tags}",
                tertiary_text=f"Description: {description}",
            )
            self.ids.account_list.add_widget(list_item)
        
        self.close_dialog()
