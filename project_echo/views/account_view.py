
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
        # Use margin instead of padding
        super().__init__(style=Pack(direction=COLUMN, flex=1, margin=10))
        self.app = app
        self.build()

    def build(self):
        for child in self.children:
            self.remove(child)
        
        # Use margin_right and margin_bottom
        add_button = toga.Button('Add Account', on_press=self.add_account_handler, style=Pack(margin_right=5))
        refresh_button = toga.Button('Refresh', on_press=self.refresh_handler)
        top_box = toga.Box(style=Pack(direction=ROW, margin_bottom=10))
        top_box.add(add_button)
        top_box.add(refresh_button)

        self.account_table = toga.Table(
            headings=['Phone', 'Status', 'Tags', 'Notes'],
            data=self.get_account_data(),
            style=Pack(flex=1),
            missing_value="N/A"
        )

        # Use margin_right and margin_top
        delete_button = toga.Button('Delete Selected', on_press=self.delete_selected_handler, style=Pack(margin_right=5))
        tags_button = toga.Button('Assign Tags/Notes', on_press=self.assign_tags_handler)
        bottom_box = toga.Box(style=Pack(direction=ROW, margin_top=10))
        bottom_box.add(delete_button)
        bottom_box.add(tags_button)

        self.add(top_box)
        self.add(self.account_table)
        self.add(bottom_box)

    def get_account_data(self):
        accounts = telegram_service.load_accounts()
        return [(
            acc.get('phone'), 
            acc.get('status', 'unknown'), 
            format_tags(acc.get('tags')), 
            acc.get('notes', ''),
            acc 
        ) for acc in accounts]

    def refresh_handler(self, widget=None):
        self.account_table.data = self.get_account_data()

    def add_account_handler(self, widget):
        self.login_window = AddAccountWindow(self.app, on_success_callback=self.refresh_handler)
        self.login_window.show()

    async def delete_account_task(self, selection):
        account_object = selection[-1]
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


class AddAccountWindow(toga.Window):
    def __init__(self, app, on_success_callback):
        super().__init__(title="Add New Telegram Account", size=(400, 250))
        self.app = app
        self.on_success_callback = on_success_callback
        self.submit_code_handler = None
        self.submit_password_handler = None

        self.phone_input = toga.TextInput(placeholder='+1234567890')
        self.code_input = toga.TextInput(placeholder='Confirmation Code')
        self.password_input = toga.TextInput(placeholder='2FA Password', password=True)
        self.status_label = toga.Label('Enter your phone number to begin.')
        self.send_code_button = toga.Button('Send Code', on_press=self.handle_send_code)
        self.login_button = toga.Button('Login', on_press=self.handle_login)
        
        self.build_layout()

    def build_layout(self):
        # Use margin instead of padding
        box = toga.Box(style=Pack(direction=COLUMN, margin=15))
        box.add(toga.Label('Phone Number:'))
        box.add(self.phone_input)
        box.add(self.send_code_button)
        box.add(toga.Label(' ')) # Spacer
        box.add(toga.Label('Confirmation Code:'))
        box.add(self.code_input)
        box.add(toga.Label('2FA Password (if required):'))
        box.add(self.password_input)
        box.add(self.login_button)
        box.add(self.status_label)
        
        self.code_input.style.visibility = 'hidden'
        self.password_input.style.visibility = 'hidden'
        self.login_button.style.visibility = 'hidden'

        self.content = box

    # ... rest of AddAccountWindow methods are unchanged ...
    def handle_send_code(self, widget):
        phone = self.phone_input.value
        if not phone:
            self.status_label.text = 'Error: Phone number cannot be empty.'
            return
        widget.enabled = False
        self.status_label.text = 'Sending code...'
        self.app.loop.create_task(self.run_add_account_flow(phone))

    async def run_add_account_flow(self, phone):
        async def on_code_request():
            self.status_label.text = 'Code sent. Please check Telegram.'
            self.code_input.style.visibility = 'visible'
            self.login_button.style.visibility = 'visible'
        async def on_password_request():
            self.status_label.text = '2FA Password required.'
            self.password_input.style.visibility = 'visible'
        async def on_success():
            self.status_label.text = 'Success! Account added.'
            self.on_success_callback()
            await asyncio.sleep(1.5)
            self.close()
        async def on_failure(error_message):
            self.status_label.text = f'Error: {error_message}'
            self.send_code_button.enabled = True

        self.submit_code_handler, self.submit_password_handler = await telegram_service.add_account(
            phone=phone,
            on_code_request=on_code_request,
            on_password_request=on_password_request,
            on_success=on_success,
            on_failure=on_failure
        )
        if not self.submit_code_handler:
             self.send_code_button.enabled = True

    def handle_login(self, widget):
        widget.enabled = False
        self.status_label.text = 'Verifying...'
        self.app.loop.create_task(self.run_login_submission())

    async def run_login_submission(self):
        code = self.code_input.value
        password = self.password_input.value
        if password and self.password_input.style.visibility == 'visible' and self.submit_password_handler:
            await self.submit_password_handler(password)
        elif code and self.submit_code_handler:
            await self.submit_code_handler(code)
        else:
            self.status_label.text = 'Error: Code is required.'
            self.login_button.enabled = True


class AssignTagsWindow(toga.Window):
    def __init__(self, app, account_data, on_success_callback):
        super().__init__(title=f"Edit Details for {account_data.get('phone')}", size=(400, 250))
        self.app = app
        self.account_data = account_data
        self.on_success_callback = on_success_callback

        current_tags = format_tags(self.account_data.get('tags'))
        current_notes = self.account_data.get('notes', '')
        self.tags_input = toga.TextInput(value=current_tags)
        self.notes_input = toga.TextInput(value=current_notes)
        self.save_button = toga.Button('Save', on_press=self.handle_save)
        self.status_label = toga.Label('Edit tags (comma-separated) and notes.')

        self.build_layout()

    def build_layout(self):
        # Use margin instead of padding
        box = toga.Box(style=Pack(direction=COLUMN, margin=15))
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
        tags_list = [tag.strip() for tag in self.tags_input.value.split(',') if tag.strip()]
        details_to_update = {
            'tags': tags_list,
            'notes': self.notes_input.value
        }
        telegram_service.update_account_details(session_name, details_to_update)
        self.status_label.text = 'Saved successfully!'
        self.on_success_callback()
        self.close()
