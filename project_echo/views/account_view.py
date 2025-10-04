
import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW, LEFT

class AccountView(toga.Box):
    def __init__(self):
        super().__init__(style=Pack(direction=COLUMN, flex=1))
        self.add(toga.Label("This is the Account View"))

        # We will add buttons, lists, and other widgets here later
