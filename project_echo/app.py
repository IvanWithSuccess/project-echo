
import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW, LEFT, RIGHT

# Import views
from project_echo.views.account_view import AccountView
from project_echo.views.ad_cabinet_view import AdCabinetView

class ProjectEcho(toga.App):

    def startup(self):
        # Main window
        self.main_window = toga.MainWindow(title=self.formal_name, size=(800, 600))

        # Main container with tabs
        self.option_container = toga.OptionContainer()

        # --- Add Views to Tabs ---
        account_manager_view = AccountView(self)
        ad_cabinet_view = AdCabinetView(self)

        # CORRECTED: Add tabs to the container's 'content'
        self.option_container.content.add('Accounts', account_manager_view)
        self.option_container.content.add('Ad Cabinet', ad_cabinet_view)

        # Add container to the main window
        self.main_window.content = self.option_container
        self.main_window.show()


def main():
    return ProjectEcho('Project Echo', 'org.beeware.project_echo')
