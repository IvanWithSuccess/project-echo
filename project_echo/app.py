
import toga
import asyncio
from toga.style import Pack
from toga.style.pack import COLUMN

# Import views
from project_echo.views.account_view import AccountView
from project_echo.views.ad_cabinet_view import AdCabinetView

class ProjectEcho(toga.App):

    def startup(self):
        self.main_window = toga.MainWindow(title=self.formal_name, size=(800, 600))
        self.option_container = toga.OptionContainer(style=Pack(flex=1))
        self.main_window.content = self.option_container
        self.main_window.show()

        # Use asyncio.create_task as recommended
        asyncio.create_task(self.add_tabs())

    async def add_tabs(self):
        # A short delay can sometimes help with UI initialization.
        await asyncio.sleep(0.05)
        
        account_manager_view = AccountView(self)
        ad_cabinet_view = AdCabinetView(self)

        self.option_container.add('Accounts', account_manager_view)
        self.option_container.add('Ad Cabinet', ad_cabinet_view)

def main():
    return ProjectEcho('Project Echo', 'org.beeware.project_echo')
