
import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW, CENTER

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
import asyncio
import os
import json

ACCOUNTS_FILE = "accounts.json"

class AccountView(toga.Box):
    def __init__(self, app):
        super().__init__(style=Pack(direction=COLUMN, padding=10))
        self.app = app
        self.accounts_data = self.load_accounts()

        # --- UI Elements ---
        self.account_list = toga.Table(
            headings=["Phone", "Username", "Status"],
            data=[(acc['phone'], acc.get('username', 'N/A'), 'Logged Out') for acc in self.accounts_data],
            style=Pack(flex=1)
        )

        self.add_button = toga.Button("Add Account", on_press=self.add_account_handler, style=Pack(padding=5))
        self.login_button = toga.Button("Login", on_press=self.login_handler, style=Pack(padding=5))
        self.delete_button = toga.Button("Delete Account", on_press=self.delete_account_handler, style=Pack(padding=5))

        button_box = toga.Box(style=Pack(direction=ROW, alignment=CENTER))
        button_box.add(self.add_button)
        button_box.add(self.login_button)
        button_box.add(self.delete_button)

        self.add(self.account_list)
        self.add(button_box)

    def load_accounts(self):
        if not os.path.exists(ACCOUNTS_FILE):
            return []
        with open(ACCOUNTS_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []

    def save_accounts(self):
        with open(ACCOUNTS_FILE, 'w') as f:
            json.dump(self.accounts_data, f, indent=4)

    def add_account_handler(self, widget):
        # Correctly create and show the new window
        self.login_window = AddAccountWindow(self.app, on_success_callback=self.refresh_handler)
        self.login_window.show()

    def login_handler(self, widget):
        # This will be implemented later
        pass

    def delete_account_handler(self, widget):
        if self.account_list.selection:
            selected_phone = self.account_list.selection.phone
            self.accounts_data = [acc for acc in self.accounts_data if acc['phone'] != selected_phone]
            self.save_accounts()
            self.refresh_handler()
        else:
            self.dialog(toga.InfoDialog("No Selection", "Please select an account."))

    def refresh_handler(self):
        self.accounts_data = self.load_accounts()
        self.account_list.data = [(acc['phone'], acc.get('username', 'N/A'), 'Logged Out') for acc in self.accounts_data]


class AddAccountWindow(toga.Window):
    def __init__(self, app, on_success_callback):
        # Initialize the parent Toga Window
        super().__init__(title="Add New Account", size=(400, 250))
        
        # This line caused the error and has been removed:
        # self.app = app 
        # A Toga Window is automatically associated with its app.

        self.on_success_callback = on_success_callback

        self.phone_input = toga.TextInput(placeholder='Phone Number (e.g., +1234567890)', style=Pack(padding=5))
        self.password_input = toga.PasswordInput(placeholder='2FA Password (if any)', style=Pack(padding=5))
        self.code_input = toga.TextInput(placeholder='Verification Code', style=Pack(padding=5))
        self.api_id_input = toga.TextInput(placeholder='API ID', style=Pack(padding=5))
        self.api_hash_input = toga.TextInput(placeholder='API Hash', style=Pack(padding=5))
        
        self.submit_button = toga.Button('Submit', on_press=self.submit_handler, style=Pack(padding=5))

        content = toga.Box(style=Pack(direction=COLUMN, padding=20))
        content.add(self.phone_input)
        content.add(self.password_input)
        content.add(self.code_input)
        content.add(self.api_id_input)
        content.add(self.api_hash_input)
        content.add(self.submit_button)

        self.content = content

    def submit_handler(self, widget):
        # Logic for submitting the new account will be added here.
        # For now, let's just save the basic info.
        new_account = {
            "phone": self.phone_input.value,
            "api_id": self.api_id_input.value,
            "api_hash": self.api_hash_input.value
        }

        accounts = self.app.main_window.content.content[0].accounts_data # A bit complex, but gets to the data
        accounts.append(new_account)
        self.app.main_window.content.content[0].save_accounts()

        # Notify the main view to refresh
        if self.on_success_callback:
            self.on_success_callback()

        # Close this window
        self.close()
