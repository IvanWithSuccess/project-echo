
from kivy.lang import Builder
from kivy.metrics import dp
from kivymd.app import MDApp # FIX: Import MDApp to access the running app instance
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.textfield import MDTextField
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
        self.menu = None

    def open_menu(self):
        """Creates the menu on first press and opens it."""
        if not self.menu:
            menu_items = [
                {
                    "viewclass": "OneLineIconListItem",
                    "text": "Add new",
                    "height": dp(48),
                    "on_release": self.go_to_login_screen,
                    "left_icon": "pencil"
                },
                {
                    "viewclass": "OneLineIconListItem",
                    "text": "Mass import",
                    "height": dp(48),
                    "on_release": self.show_api_import_dialog,
                    "left_icon": "cloud-upload-outline"
                }
            ]
            self.menu = MDDropdownMenu(
                caller=self.ids.add_button,
                items=menu_items,
                position="top",
                width_mult=3.5,
            )
        self.menu.open()

    # FIX: Renamed and repurposed this method to switch screens
    def go_to_login_screen(self):
        """Switches the screen to the login screen."""
        if self.menu:
            self.menu.dismiss()
        # Access the app's root and switch the screen
        MDApp.get_running_app().root.ids.screen_manager.current = 'login_screen'
    
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
