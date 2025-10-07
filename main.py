import tkinter as tk
from tkinter import ttk
import asyncio
import threading

# We will keep the TelegramService as it is essential for the core logic.
from project_echo.services.telegram_service import TelegramService

class ProjectEchoApp:
    """
    Main application class using Tkinter.
    """
    def __init__(self, root):
        self.root = root
        self.root.title("Project Echo")
        # Set a default size, which can be adjusted based on the final design.
        self.root.geometry("1024x768")

        self.telegram_service = TelegramService()

        # This method will be used to build the UI based on your HTML UI kit.
        self.create_login_screen()

    def create_login_screen(self):
        """
        Creates and displays the login screen UI.
        This will be implemented based on the provided UI kit.
        """
        # Placeholder content for now
        container = ttk.Frame(self.root, padding=20)
        container.pack(expand=True)

        label = ttk.Label(container, text="Project Echo (Tkinter)")
        label.pack(pady=10)

        placeholder_button = ttk.Button(container, text="Ready for UI Kit")
        placeholder_button.pack(pady=10)

    def run_async(self, coro):
        """
        Runs an asynchronous task in a separate thread to avoid blocking the UI.
        This is crucial for network operations with Telegram.
        """
        threading.Thread(target=asyncio.run, args=(coro,)).start()

def main():
    """
    Initializes and runs the Tkinter application.
    """
    root = tk.Tk()
    app = ProjectEchoApp(root)
    root.mainloop()

if __name__ == '__main__':
    main()
