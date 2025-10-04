
import toga
from toga.style import Pack
from toga.style.pack import COLUMN

# Import views
from project_echo.views.account_view import AccountView
from project_echo.views.ad_cabinet_view import AdCabinetView

class ProjectEcho(toga.App):

    def startup(self):
        # 1. Create the main window.
        self.main_window = toga.MainWindow(title=self.formal_name, size=(800, 600))

        # 2. Create the views that will be the content of the tabs *first*.
        account_manager_view = AccountView(self)
        ad_cabinet_view = AdCabinetView(self)

        # 3. Create the OptionContainer and provide the tabs directly
        #    to the 'content' argument during initialization.
        option_container = toga.OptionContainer(
            style=Pack(flex=1),
            content=[
                ('Accounts', account_manager_view),
                ('Ad Cabinet', ad_cabinet_view)
            ]
        )

        # 4. Set the fully-constructed container as the content of the window.
        self.main_window.content = option_container

        # 5. Show the window.
        self.main_window.show()

def main():
    return ProjectEcho('Project Echo', 'org.beeware.project_echo')
