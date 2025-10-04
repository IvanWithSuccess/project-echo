
import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

from project_echo.views.account_view import AccountView
# from project_echo.views.ad_cabinet_view import AdCabinetView # We'll use this later

class ProjectEcho(toga.App):

    def startup(self):
        self.main_window = toga.MainWindow(title=self.formal_name, size=(800, 600))

        # Create a split container to hold the navigation and content
        self.split_container = toga.SplitContainer()

        # --- Navigation --- #
        self.nav_tree = toga.Tree(
            ['Accounts', 'Ad Cabinet'],
            on_select=self.on_nav_select,
            style=Pack(width=150)
        )

        # --- Content Area --- #
        self.account_view = AccountView()
        # self.ad_cabinet_view = AdCabinetView() # We'll use this later
        self.content = toga.Box(style=Pack(flex=1))
        self.content.add(self.account_view)

        # Add navigation and content to the split container
        self.split_container.content = [(self.nav_tree, 1), (self.content, 5)]

        self.main_window.content = self.split_container
        self.main_window.show()

    def on_nav_select(self, widget, node):
        if node and node.text == 'Accounts':
            self.content.clear()
            self.content.add(self.account_view)
        elif node and node.text == 'Ad Cabinet':
            self.content.clear()
            # self.content.add(self.ad_cabinet_view)
            pass # We'll implement this later

def main():
    return ProjectEcho('Project Echo', 'org.beeware.project_echo')
