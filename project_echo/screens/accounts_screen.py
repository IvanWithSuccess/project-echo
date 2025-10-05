from kivy.lang import Builder
from kivy.metrics import dp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.list import ThreeLineAvatarIconListItem, IconLeftWidget
# FIX: Import MDDropdownMenu
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
        self.menu = None

    # FIX: Create the dropdown menu after the layout is ready
    def on_kv_post(self, base_widget):
        """Called after the kv file is loaded. Creates the dropdown menu."""
        menu_items = [
            {
                "viewclass": "OneLineIconListItem",
                "text": "Add manually",
                "height": dp(56),
                "on_release": self.show_add_account_dialog,
                "IconLeftWidget": {
                    "icon": "pencil"
                }
            },
            {
                "viewclass": "OneLineIconListItem",
                "text": "Import from API",
                "height": dp(56),
                "on_release": lambda: print("API Import placeholder"),
                "IconLeftWidget": {
                    "icon": "cloud-upload-outline"
                }
            }
        ]
        self.menu = MDDropdownMenu(
            caller=self.ids.add_button,
            items=menu_items,
            width_mult=4,
        )

    # FIX: Method to open the menu
    def open_menu(self):
        """Opens the dropdown menu."""
        self.menu.open()

    def show_add_account_dialog(self):
        """Creates and shows a new 'Add Account' dialog."""
        if self.menu: # Close the menu before opening the dialog
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
