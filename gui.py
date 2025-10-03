import flet as ft

def main(page: ft.Page):
    page.title = "Telegram Client"
    page.add(
        ft.Text("Welcome to your Telegram Client!")
    )

ft.app(target=main, view=ft.AppView.WEB_BROWSER)
