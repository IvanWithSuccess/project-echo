
import toga
from toga.style import Pack
from toga.style.pack import COLUMN

# Import views
from project_echo.views.account_view import AccountView
from project_echo.views.ad_cabinet_view import AdCabinetView

class ProjectEcho(toga.App):

    def startup(self):
        # 1. Create the main window
        self.main_window = toga.MainWindow(title=self.formal_name, size=(800, 600))

        # 2. Create a root container box that will hold everything.
        # This provides a stable parent for the OptionContainer.
        root_box = toga.Box(style=Pack(direction=COLUMN, flex=1))

        # 3. Create the tab container and make it expand to fill the root_box.
        self.option_container = toga.OptionContainer(style=Pack(flex=1))

        # 4. Add the tab container to the root box *before* we add content to the tabs.
        root_box.add(self.option_container)

        # 5. Now, create the views that will go inside the tabs.
        account_manager_view = AccountView(self)
        ad_cabinet_view = AdCabinetView(self)

        # 6. With the hierarchy established, add the views as tabs.
        self.option_container.add('Accounts', account_manager_view)
        self.option_container.add('Ad Cabinet', ad_cabinet_view)

        # 7. Set the stable root_box as the content of the main window.
        self.main_window.content = root_box

        # 8. Show the window.
        self.main_window.show()


def main():
    return ProjectEcho('Project Echo', 'org.beeware.project_echo')
