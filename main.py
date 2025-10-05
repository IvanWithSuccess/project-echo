
import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner

kivy.require('2.1.0') # Ensure compatibility

# ==========================================================================
# >> KIVY WIDGETS & LAYOUTS
# ==========================================================================

class AccountsPanel(BoxLayout):
    """Content for the 'Accounts' tab."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = [10, 10, 10, 10]
        self.spacing = 10

        # --- Toolbar ---
        toolbar = BoxLayout(size_hint_y=None, height=48, spacing=10)
        
        # 'Create Account' Button
        create_button = Button(text='Create Account', size_hint_x=None, width=150)
        toolbar.add_widget(create_button)

        # Spacer
        toolbar.add_widget(BoxLayout()) # This pushes the filter to the right

        # Status Filter
        status_filter = Spinner(
            text='Any Status',
            values=('Any Status', 'Active', 'Inactive'),
            size_hint_x=None,
            width=150
        )
        toolbar.add_widget(status_filter)
        self.add_widget(toolbar)

        # --- Data Table Placeholder ---
        table_placeholder = Label(text='Accounts data table will be here.')
        self.add_widget(table_placeholder)


class MainAppLayout(BoxLayout):
    """The root widget of the application."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'

        # Create the main tabbed panel
        tab_panel = TabbedPanel(do_default_tab=False)

        # --- Accounts Tab (Set as default) ---
        accounts_tab = TabbedPanelItem(text='Accounts')
        accounts_tab.add_widget(AccountsPanel())
        tab_panel.add_widget(accounts_tab)
        tab_panel.switch_to(accounts_tab) # Make it the default

        # --- Dashboard Tab ---
        dashboard_tab = TabbedPanelItem(text='Dashboard')
        dashboard_tab.add_widget(Label(text='Dashboard content will be here.'))
        tab_panel.add_widget(dashboard_tab)

        # --- Campaigns Tab ---
        campaigns_tab = TabbedPanelItem(text='Campaigns')
        campaigns_tab.add_widget(Label(text='Campaigns content will be here.'))
        tab_panel.add_widget(campaigns_tab)

        self.add_widget(tab_panel)

# ==========================================================================
# >> KIVY APP CLASS
# ==========================================================================

class ProjectEchoApp(App):
    def build(self):
        self.title = 'Project Echo'
        return MainAppLayout()

# ==========================================================================
# >> MAIN EXECUTION
# ==========================================================================

if __name__ == '__main__':
    # Note: setup_directories() from the old web server is no longer needed
    # unless we decide to save/load files from specific Kivy-related paths.
    ProjectEchoApp().run()
