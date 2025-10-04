
import toga
from toga.style import Pack

# Import views
from project_echo.views.account_view import AccountView
from project_echo.views.ad_cabinet_view import AdCabinetView

class ProjectEcho(toga.App):

    def startup(self):
        # 1. Create the main window
        self.main_window = toga.MainWindow(title=self.formal_name, size=(800, 600))

        # 2. Create the tab container
        self.option_container = toga.OptionContainer()

        # 3. IMPORTANT: Assign the container to the window *before* adding content
        self.main_window.content = self.option_container

        # 4. Create the content for the tabs
        account_manager_view = AccountView(self)
        ad_cabinet_view = AdCabinetView(self)

        # 5. Now, add the tabs to the container
        self.option_container.add('Accounts', account_manager_view)
        self.option_container.add('Ad Cabinet', ad_cabinet_view)

        # 6. Show the main window
        self.main_window.show()


def main():
    return ProjectEcho('Project Echo', 'org.beeware.project_echo')
