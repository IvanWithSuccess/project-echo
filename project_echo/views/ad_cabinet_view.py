
import toga
import asyncio
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

from ..services.telegram_service import telegram_service

class AdCabinetView(toga.Box):
    def __init__(self, app):
        super().__init__(style=Pack(direction=COLUMN, flex=1, padding=10))
        self.app = app
        self.build()

    def build(self):
        # --- Account Selection ---
        self.account_selector = toga.Selection(on_select=self.load_dialogs_handler)
        refresh_button = toga.Button('Refresh Accounts', on_press=self.populate_account_selector, style=Pack(padding_left=10))
        
        top_box = toga.Box(style=Pack(direction=ROW, padding_bottom=10, alignment='center'))
        top_box.add(toga.Label('Select Account:', style=Pack(padding_right=10)))
        top_box.add(self.account_selector)
        top_box.add(refresh_button)

        # --- Dialogs Table ---
        self.dialogs_table = toga.Table(
            headings=['Name', 'Type', 'ID'],
            style=Pack(flex=1),
            missing_value='N/A'
        )

        self.add(top_box)
        self.add(self.dialogs_table)
        
        # Initial population
        self.populate_account_selector()

    def populate_account_selector(self, widget=None):
        """Refreshes the list of accounts in the dropdown."""
        accounts = telegram_service.load_accounts()
        active_accounts = [acc for acc in accounts if acc.get('status') == 'active']
        
        current_selection_value = None
        if self.account_selector.value:
            current_selection_value = self.account_selector.value[1] # session_name

        # The items are tuples of (display_text, value_object)
        self.account_selector.items = [(acc['phone'], acc['session_name']) for acc in active_accounts]

        # Try to restore the previous selection
        if current_selection_value:
            for item in self.account_selector.items:
                if item[1] == current_selection_value:
                    self.account_selector.value = item
                    break
            else: # If the loop finished without finding the item
                self.dialogs_table.data.clear()

    def load_dialogs_handler(self, widget):
        """Handles a new selection in the account dropdown."""
        self.dialogs_table.data.clear() # Clear table on new selection
        
        if not widget.value:
            self.app.main_window.status = "Select an account"
            return
        
        session_name = widget.value[1] # Get session_name from the tuple
        self.app.main_window.status = f"Loading chats for {session_name}..."
        self.app.loop.create_task(self.load_dialogs_task(session_name))
    
    async def load_dialogs_task(self, session_name):
        """The async task that fetches and displays dialogs."""
        dialogs = await telegram_service.get_dialogs(session_name)
        if dialogs:
            self.dialogs_table.data = [
                (d['name'], self.get_dialog_type(d), str(d['id'])) # Ensure ID is a string for display
                for d in dialogs
            ]
            self.app.main_window.status = f"Loaded {len(dialogs)} chats."
        else:
            self.app.main_window.status = f"Failed to load or no chats found for {session_name}."

    @staticmethod
    def get_dialog_type(dialog):
        if dialog['is_channel']:
            return 'Channel'
        if dialog['is_group']:
            return 'Group'
        if dialog['is_user']:
            return 'User'
        return 'Unknown'
