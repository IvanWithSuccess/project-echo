
import toga
import asyncio
from toga.style import Pack
from toga.style.pack import COLUMN, ROW, LEFT

from ..services.telegram_service import telegram_service

# Helper to format tags
def format_tags(tags_list):
    if not tags_list:
        return ""
    return ", ".join(tags_list)

class AccountView(toga.Box):
    def __init__(self, app):
        super().__init__(style=Pack(direction=COLUMN, flex=1, padding=10))
        self.app = app
        self.build()

    def build(self):
        for child in self.children:
            self.remove(child)
        
        add_button = toga.Button('Add Account', on_press=self.add_account_handler, style=Pack(padding_right=5))
        refresh_button = toga.Button('Refresh', on_press=self.refresh_handler)
        top_box = toga.Box(style=Pack(direction=ROW, padding_bottom=10))
        top_box.add(add_button)
        top_box.add(refresh_button)

        self.account_table = toga.Table(
            headings=['Phone', 'Status', 'Tags', 'Notes'], # Added 'Tags'
            data=self.get_account_data(),
            style=Pack(flex=1),
            missing_value="N/A"
        )

        delete_button = toga.Button('Delete Selected', on_press=self.delete_selected_handler, style=Pack(padding_right=5))
        tags_button = toga.Button('Assign Tags/Notes', on_press=self.assign_tags_handler)
        bottom_box = toga.Box(style=Pack(direction=ROW, padding_top=10))
        bottom_box.add(delete_button)
        bottom_box.add(tags_button)

        self.add(top_box)
        self.add(self.account_table)
        self.add(bottom_box)

    def get_account_data(self):
        accounts = telegram_service.load_accounts()
        # Return a list of toga.ListSource compatible rows
        return [(
            acc.get('phone'), 
            acc.get('status', 'unknown'), 
            format_tags(acc.get('tags')), # Format tags for display
            acc.get('notes', ''),
            acc # Store the original object to get session_name later
        ) for acc in accounts]

    def refresh_handler(self, widget=None):
        self.account_table.data = self.get_account_data()

    def add_account_handler(self, widget):
        self.login_window = AddAccountWindow(self.app, on_success_callback=self.refresh_handler)
        self.login_window.show()

    async def delete_account_task(self, selection):
        account_object = selection[-1] # The original account object is the last item
        session_name = account_object.get('session_name')
        if not session_name:
            self.app.main_window.error_dialog("Deletion Error", "Could not find session name.")
            return

        await telegram_service.delete_account(session_name)
        self.refresh_handler()
        self.app.main_window.info_dialog("Success", f"Account {account_object.get('phone')} deleted.")

    def delete_selected_handler(self, widget):
        if not self.account_table.selection:
            self.app.main_window.info_dialog("No Selection", "Please select an account.")
            return
        
        phone = self.account_table.selection[0]
        confirmed = self.app.main_window.confirm_dialog(f"Delete {phone}?", f"Are you sure?")
        if confirmed:
            self.app.loop.create_task(self.delete_account_task(self.account_table.selection))

    def assign_tags_handler(self, widget):
        if not self.account_table.selection:
            self.app.main_window.info_dialog('Selection Error', 'Please select an account first.')
            return

        account_object = self.account_table.selection[-1]
        self.tags_window = AssignTagsWindow(self.app, account_object, on_success_callback=self.refresh_handler)
        self.tags_window.show()

# --- Window for Adding Accounts (no changes) ---
class AddAccountWindow(toga.Window):
    # ... (code is identical to previous version)
    pass

# --- NEW: Window for Assigning Tags and Notes ---
class AssignTagsWindow(toga.Window):
    def __init__(self, app, account_data, on_success_callback):
        super().__init__(title=f"Edit Details for {account_data.get('phone')}", size=(400, 250))
        self.app = app
        self.account_data = account_data
        self.on_success_callback = on_success_callback

        # --- UI Elements ---
        current_tags = format_tags(self.account_data.get('tags'))
        current_notes = self.account_data.get('notes', '')
        self.tags_input = toga.TextInput(value=current_tags)
        self.notes_input = toga.TextInput(value=current_notes)
        self.save_button = toga.Button('Save', on_press=self.handle_save)
        self.status_label = toga.Label('Edit tags (comma-separated) and notes.')

        self.build_layout()

    def build_layout(self):
        box = toga.Box(style=Pack(direction=COLUMN, padding=15))
        box.add(toga.Label('Tags (comma-separated):'))
        box.add(self.tags_input)
        box.add(toga.Label('Notes:'))
        box.add(self.notes_input)
        box.add(self.save_button)
        box.add(self.status_label)
        self.content = box

    def handle_save(self, widget):
        self.status_label.text = 'Saving...'
        session_name = self.account_data.get('session_name')

        # Parse tags from string to list, stripping whitespace
        tags_list = [tag.strip() for tag in self.tags_input.value.split(',') if tag.strip()]
        
        details_to_update = {
            'tags': tags_list,
            'notes': self.notes_input.value
        }

        telegram_service.update_account_details(session_name, details_to_update)
        
        self.status_label.text = 'Saved successfully!'
        self.on_success_callback() # Refresh main table
        self.close()
