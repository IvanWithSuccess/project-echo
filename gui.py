
import flet as ft
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
import asyncio

# Replace with your actual API ID and Hash
api_id = 26947469
api_hash = '731a222f9dd8b290db925a6a382159dd'

async def main(page: ft.Page):
    page.title = "Telegram Client"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    client_holder = {"client": None}

    async def show_chat_messages(client: TelegramClient, chat_id: int, chat_name: str):
        page.clean()
        page.title = f"Chat: {chat_name}"

        async def go_back(e):
            await show_dialogs(client)

        back_button = ft.ElevatedButton("Back to Chats", on_click=go_back)
        messages_list_view = ft.ListView(expand=1, spacing=10, auto_scroll=True)

        page.add(
            ft.Row([back_button], alignment=ft.MainAxisAlignment.START),
            ft.Text(f"Messages for {chat_name}", size=20, weight=ft.FontWeight.BOLD),
            messages_list_view
        )
        page.update()

        try:
            messages = []
            async for message in client.iter_messages(chat_id, limit=50):
                sender = await message.get_sender()
                sender_name = sender.first_name if hasattr(sender, 'first_name') else "Unknown"
                messages.append(ft.Text(f"{sender_name}: {message.text}"))
            
            messages.reverse() # Show newest messages at the bottom
            messages_list_view.controls.extend(messages)

        except Exception as e:
            messages_list_view.controls.append(ft.Text(f"Error loading messages: {e}"))

        page.update()

    async def show_dialogs(client: TelegramClient):
        page.clean()
        page.title = "My Chats"
        
        status_text = ft.Text("Loading chats...")
        dialogs_list_view = ft.ListView(expand=1, spacing=10, auto_scroll=True)
        
        async def on_chat_click(e):
            chat_id = e.control.data
            chat_name = e.control.title.value
            await show_chat_messages(client, chat_id, chat_name)

        page.add(
            ft.Row([ft.Text("Your Chats", size=24, weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.CENTER),
            status_text,
            dialogs_list_view
        )
        page.update()

        try:
            async for dialog in client.iter_dialogs():
                dialogs_list_view.controls.append(
                    ft.ListTile(
                        title=ft.Text(dialog.name),
                        data=dialog.id,
                        on_click=on_chat_click
                    )
                )
            status_text.value = "Chats loaded successfully."
        except Exception as e:
            status_text.value = f"Error loading chats: {e}"
        
        page.update()

    # --- UI Elements for Login ---
    session_name_field = ft.TextField(label="Session Name (e.g., account1)", width=300)
    phone_number_field = ft.TextField(label="Phone Number (+1234567890)", width=300)
    code_field = ft.TextField(label="Confirmation Code", width=300, visible=False)
    password_field = ft.TextField(label="2FA Password", password=True, width=300, visible=False)
    login_button = ft.ElevatedButton(text="Get Code", width=300)
    status_text_login = ft.Text()

    async def get_code_click(e):
        session_name = session_name_field.value.strip()
        phone_number = phone_number_field.value.strip()

        if not session_name or not phone_number:
            status_text_login.value = "Please fill in all fields."
            page.update()
            return

        client = TelegramClient(session_name, api_id, api_hash)
        client_holder["client"] = client
        await client.connect()

        if not await client.is_user_authorized():
            status_text_login.value = "Sending confirmation code..."
            page.update()
            try:
                await client.send_code_request(phone_number)
                phone_number_field.visible = False
                code_field.visible = True
                login_button.text = "Sign In"
                status_text_login.value = "Code sent. Please check your Telegram app."
            except Exception as ex:
                status_text_login.value = f"Error: {ex}"
        else:
            status_text_login.value = "You are already signed in. Transitioning to chats..." 
            await show_dialogs(client)

        page.update()

    async def sign_in_click(e):
        client = client_holder.get("client")
        if not client:
            status_text_login.value = "Client not initialized. Please start over."
            page.update()
            return

        try:
            if password_field.visible:
                await client.sign_in(password=password_field.value.strip())
            else:
                await client.sign_in(phone_number_field.value.strip(), code_field.value.strip())
            
            me = await client.get_me()
            status_text_login.value = f"Welcome, {me.first_name}! Successfully signed in."
            page.update()
            await asyncio.sleep(1) # a short delay to show the welcome message
            await show_dialogs(client)

        except SessionPasswordNeededError:
            password_field.visible = True
            login_button.text = "Sign In with Password"
            status_text_login.value = "2FA enabled. Please enter your password."
        except Exception as ex:
            status_text_login.value = f"Sign-in error: {ex}"
        
        page.update()

    async def button_logic_handler(e):
        if login_button.text == "Get Code":
            await get_code_click(e)
        else:
            await sign_in_click(e)

    login_button.on_click = button_logic_handler

    # --- Initial Login View ---
    login_view = ft.Column(
        [
            ft.Text("Telegram Account Registration", size=24, weight=ft.FontWeight.BOLD),
            session_name_field,
            phone_number_field,
            code_field,
            password_field,
            login_button,
            status_text_login,
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=20
    )
    page.add(login_view)

if __name__ == "__main__":
    ft.app(target=main)
