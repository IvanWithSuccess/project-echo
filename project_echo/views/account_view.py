
import toga
import asyncio
from toga.style import Pack
from toga.style.pack import COLUMN, ROW, CENTER

import json
import os

# Import the new service
from project_echo.services.telegram_service import TelegramService

ACCOUNTS_FILE = "accounts.json"

# --- Main Account Management View ---
class AccountView(toga.Box):
    def __init__(self, app):
        # Fix DeprecationWarning: padding -> margin
        super().__init__(style=Pack(direction=COLUMN, margin=10))
        self.app = app
        self.accounts_data = self.load_accounts()

        self.account_list = toga.Table(
            headings=["Phone", "Username", "Status"],
            data=[(acc.get('phone', 'N/A'), acc.get('username', 'N/A'), 'Logged Out') for acc in self.accounts_data],
            style=Pack(flex=1),
            missing_value='N/A'
        )

        # Fix DeprecationWarning: padding -> margin
        self.add_button = toga.Button("Add Account", on_press=self.add_account_handler, style=Pack(margin=5))
        self.login_button = toga.Button("Login", on_press=self.login_handler, style=Pack(margin=5))
        self.delete_button = toga.Button("Delete Account", on_press=self.delete_account_handler, style=Pack(margin=5))

        # Fix DeprecationWarning: alignment -> align_items
        button_box = toga.Box(style=Pack(direction=ROW, align_items=CENTER))
        button_box.add(self.add_button)
        button_box.add(self.login_button)
        button_box.add(self.delete_button)

        self.add(self.account_list)
        self.add(button_box)

    def load_accounts(self):
        if not os.path.exists(ACCOUNTS_FILE):
            return []
        try:
            with open(ACCOUNTS_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def save_accounts(self):
        with open(ACCOUNTS_FILE, 'w') as f:
            json.dump(self.accounts_data, f, indent=4)

    def add_account_handler(self, widget):
        add_window = AddAccountWindow(self.app, on_success_callback=self.refresh_handler)
        add_window.show()

    async def login_handler(self, widget):
        # Fix AttributeError: Call dialog from the main window, not the Box
        self.app.main_window.dialog(toga.InfoDialog("TODO", "Login functionality will be implemented soon!"))

    def delete_account_handler(self, widget):
        if self.account_list.selection:
            # Correctly get phone from selection
            selected_phone = self.account_list.selection[0].phone
            self.accounts_data = [acc for acc in self.accounts_data if acc['phone'] != selected_phone]
            self.save_accounts()
            self.refresh_handler()
        else:
            # Fix AttributeError: Call dialog from the main window
            self.app.main_window.dialog(toga.InfoDialog("No Selection", "Please select an account."))
        
    def refresh_handler(self):
        self.accounts_data = self.load_accounts()
        self.account_list.data = [(acc.get('phone', 'N/A'), acc.get('username', 'N/A'), 'Logged Out') for acc in self.accounts_data]
        self.account_list.refresh()


# --- The New, Step-by-Step Add Account Window ---
class AddAccountWindow(toga.Window):
    def __init__(self, app, on_success_callback):
        super().__init__(title="Add New Account", size=(400, 200))
        # The `app` attribute is automatically assigned by Toga.
        # Manually assigning it with `self.app = app` caused the ValueError.
        self.on_success_callback = on_success_callback
        self.telegram_service = None

        # --- UI Elements (with DeprecationWarning fixes) ---
        self.phone_input = toga.TextInput(placeholder='Phone (+123...)', style=Pack(margin=(10,5,0,5)))
        self.code_input = toga.TextInput(placeholder='Verification Code', style=Pack(margin=(5,5,0,5)))
        self.password_input = toga.PasswordInput(placeholder='2FA Password', style=Pack(margin=(5,5,0,5)))
        self.status_label = toga.Label("Enter your phone number to begin.", style=Pack(margin=(10,5)))
        self.submit_button = toga.Button('Send Code', on_press=self.submit_handler, style=Pack(margin=15))

        self.code_input.style.visibility = 'hidden'
        self.password_input.style.visibility = 'hidden'

        content = toga.Box(style=Pack(direction=COLUMN))
        content.add(self.status_label)
        content.add(self.phone_input)
        content.add(self.code_input)
        content.add(self.password_input)
        content.add(self.submit_button)
        self.content = content
        
        self.current_state = 'phone'

    async def submit_handler(self, widget):
        widget.enabled = False
        try:
            if self.current_state == 'phone':
                self.status_label.text = 'Connecting and sending code...'
                phone = self.phone_input.value
                if not phone:
                    self.dialog(toga.InfoDialog('Error', 'Phone number is required.'))
                    return
                
                self.telegram_service = TelegramService(phone)
                success = await self.telegram_service.start_login()

                if success:
                    self.status_label.text = 'Code sent! Please enter it below.'
                    self.phone_input.readonly = True
                    self.code_input.style.visibility = 'visible'
                    self.submit_button.text = 'Submit Code'
                    self.current_state = 'code'
                else:
                    self.dialog(toga.ErrorDialog('Login Error', 'Failed to send verification code.'))
                    self.close()

            elif self.current_state == 'code':
                self.status_label.text = 'Verifying code...'
                result = await self.telegram_service.submit_code(self.code_input.value)
                
                if result == 'SUCCESS':
                    await self.finish_login()
                elif result == 'PASSWORD_NEEDED':
                    self.status_label.text = '2FA Password Required.'
                    self.code_input.readonly = True
                    self.password_input.style.visibility = 'visible'
                    self.submit_button.text = 'Submit Password'
                    self.current_state = 'password'
                else:
                    self.dialog(toga.ErrorDialog('Login Error', f'Invalid code: {result}'))
            
            elif self.current_state == 'password':
                self.status_label.text = 'Verifying password...'
                result = await self.telegram_service.submit_password(self.password_input.value)

                if result == 'SUCCESS':
                    await self.finish_login()
                else:
                    self.dialog(toga.ErrorDialog('Login Error', f'Invalid password: {result}'))

        finally:
            widget.enabled = True

    async def finish_login(self):
        self.status_label.text = 'Success! Fetching user info...'
        me = await self.telegram_service.get_me()
        if me:
            new_account = {
                'phone': self.telegram_service.session_name,
                'api_id': self.telegram_service.client.api_id,
                'api_hash': self.telegram_service.client.api_hash,
                'user_id': me.id,
                'username': me.username or 'N/A'
            }
            
            # Access AccountView through the app's main window content
            account_view = self.app.main_window.content.content[0]
            account_view.accounts_data.append(new_account)
            account_view.save_accounts()
            
            self.dialog(toga.InfoDialog('Success', f'Account {me.username} added successfully!'))
            if self.on_success_callback:
                self.on_success_callback()
            self.close()
        else:
             self.dialog(toga.ErrorDialog('Error', 'Could not fetch user details after login.'))
