
import toga
from toga.style import Pack
from toga.style.pack import COLUMN

# Import views
from project_echo.views.account_view import AccountView
from project_echo.views.ad_cabinet_view import AdCabinetView

class ProjectEcho(toga.App):

    def startup(self):
        # 1. Create the main window and tab container
        self.main_window = toga.MainWindow(title=self.formal_name, size=(800, 600))
        self.option_container = toga.OptionContainer(style=Pack(flex=1))

        # 2. Set the (empty) tab container as the window's content
        self.main_window.content = self.option_container

        # 3. Show the window *before* adding content to the tabs.
        # This can help resolve lifecycle issues on some platforms.
        self.main_window.show()

        # 4. Defer the addition of tabs slightly by scheduling it on the app's main loop.
        # This gives the UI time to fully initialize.
        self.add_background_task(self.add_tabs)

    async def add_tabs(self, widget, **kwargs):
        # 5. Create the actual views/content for the tabs.
        account_manager_view = AccountView(self)
        ad_cabinet_view = AdCabinetView(self)

        # 6. Now, add the tabs to the already-visible container.
        self.option_container.add('Accounts', account_manager_view)
        self.option_container.add('Ad Cabinet', ad_cabinet_view)

def main():
    return ProjectEcho('Project Echo', 'org.beeware.project_echo')
