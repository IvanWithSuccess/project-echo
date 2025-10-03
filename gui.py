
import flet as ft
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
import asyncio
import os

# Replace with your actual API ID and Hash
api_id = 26947469
api_hash = '731a222f9dd8b290db925a6a382159dd'

async def main(page: ft.Page):
    page.title = "Telegram Client"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    client_holder = {"client": None}

    # --- View: Chat Messages (with Auto-Update and Send) ---
    async def show_chat_messages(client: TelegramClient, chat_id: int, chat_name: str):
        page.clean()
        page.title = f"Chat: {chat_name}"

        messages_list_view = ft.ListView(expand=True, spacing=10, auto_scroll=True, follow=True)

        # Handler for new messages (both incoming and outgoing)
        async def on_new_message(event):
            sender = await event.get_sender()
            sender_name = sender.first_name if hasattr(sender, 'first_name') else "You" # Simplified sender logic
            messages_list_view.controls.append(ft.Text(f"{sender_name}: {event.text}"))
            page.update()

        client.add_event_handler(on_new_message, events.NewMessage(chats=chat_id))

        async def go_back(e):
            client.remove_event_handler(on_new_message) # Crucial: remove handler
            await show_dialogs(client)

        back_button = ft.ElevatedButton("Back to Chats", on_click=go_back)
        
        # --- Message Input and Send Button ---
        message_input = ft.TextField(hint_text="Type a message...", expand=True)

        async def send_message_click(e):
            message_text = message_input.value
            if message_text:
                await client.send_message(chat_id, message_text)
                message_input.value = "" # Clear input field
                page.update()

        send_button = ft.IconButton(icon=ft.icons.SEND_ROUNDED, on_click=send_message_click)

        page.add(
            ft.Row([back_button], alignment=ft.MainAxisAlignment.START),
            ft.Text(f"Messages for {chat_name}", size=20, weight=ft.FontWeight.BOLD),
            messages_list_view,
            ft.Row([message_input, send_button])
        )
        page.update()

        # Load initial messages
        try:
            messages = []
            async for message in client.iter_messages(chat_id, limit=50):
                sender = await message.get_sender()
                sender_name = sender.first_name if hasattr(sender, 'first_name') else "You"
                messages.append(ft.Text(f"{sender_name}: {message.text}"))
            
            messages.reverse()
            messages_list_view.controls.extend(messages)
        except Exception as e:
            messages_list_view.controls.append(ft.Text(f"Error loading messages: {e}"))

        page.update()

    # --- View: Dialogs/Chats List (with Unread Counts and Last Message) ---
    async def show_dialogs(client: TelegramClient):
        page.clean()
        page.title = "My Chats"
        
        status_text = ft.Text("Loading chats...")
        dialogs_list_view = ft.ListView(expand=1, spacing=10)
        
        async def on_chat_click(e):
            await show_chat_messages(client, e.control.data, e.control.title.value)

        page.add(
            ft.Row([ft.Text("Your Chats", size=24, weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.CENTER),
            status_text,
            dialogs_list_view
        )
        page.update()

        try:
            async for dialog in client.iter_dialogs():
                subtitle_text = ""
                if dialog.message:
                    if dialog.message.out:
                        subtitle_text = f"You: {dialog.message.text}"
                    else:
                        subtitle_text = dialog.message.text
                
                trailing_widget = None
                if dialog.unread_count > 0:
                    trailing_widget = ft.CircleAvatar(
                        content=ft.Text(str(dialog.unread_count), color="white"),
                        bgcolor=ft.colors.BLUE_400,
                        radius=14
                    )

                dialogs_list_view.controls.append(
                    ft.ListTile(
                        title=ft.Text(dialog.name, weight=ft.FontWeight.BOLD),
                        subtitle=ft.Text(subtitle_text, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, size=14),
                        trailing=trailing_widget,
                        data=dialog.id,
                        on_click=on_chat_click
                    )
                )
            status_text.visible = False
        except Exception as e:
            status_text.value = f"Error loading chats: {e}"
        page.update()

    # --- View: Login/Registration Form ---
    def show_login_form(session_name=None):
        page.clean()
        page.title = "Telegram Registration"

        session_name_field = ft.TextField(label="Session Name", value=session_name, disabled=bool(session_name), width=300)
        phone_number_field = ft.TextField(label="Phone Number (+1234567890)", width=300)
        code_field = ft.TextField(label="Confirmation Code", width=300, visible=False)
        password_field = ft.TextField(label="2FA Password", password=True, width=300, visible=False)
        action_button = ft.ElevatedButton(text="Get Code", width=300)
        status_text = ft.Text()

        async def button_click_handler(e):
            btn_text = e.control.text
            client = client_holder.get("client")

            try:
                if btn_text == "Get Code":
                    s_name = session_name_field.value.strip()
                    phone = phone_number_field.value.strip()
                    if not s_name or not phone: 
                        status_text.value = "Session and Phone are required."
                        page.update()
                        return
                    
                    client = TelegramClient(s_name, api_id, api_hash)
                    client_holder["client"] = client
                    await client.connect()
                    await client.send_code_request(phone)

                    phone_number_field.visible = False
                    code_field.visible = True
                    action_button.text = "Sign In"
                    status_text.value = "Code sent. Please check Telegram."
                
                elif btn_text in ["Sign In", "Sign In with Password"]:
                    if not client: return
                    if password_field.visible:
                        await client.sign_in(password=password_field.value.strip())
                    else:
                        await client.sign_in(phone_number_field.value.strip(), code_field.value.strip())
                    
                    await show_dialogs(client)

            except SessionPasswordNeededError:
                password_field.visible = True
                action_button.text = "Sign In with Password"
                status_text.value = "2FA enabled. Please enter your password."
            except Exception as ex:
                status_text.value = f"Error: {ex}"
            page.update()

        action_button.on_click = button_click_handler
        page.add(ft.Column([
            ft.Text("Account Registration", size=24), session_name_field, phone_number_field,
            code_field, password_field, action_button, status_text
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20))
        page.update()

    # --- View: Initial Welcome/Session Selector ---
    def show_welcome_view():
        page.clean()
        page.title = "Welcome"

        session_files = [f for f in os.listdir('.') if f.endswith('.session')]
        session_options = [ft.dropdown.Option(s) for s in session_files]
        session_dropdown = ft.Dropdown(label="Select existing session", options=session_options, width=300)

        async def login_with_session(e):
            session_name = session_dropdown.value
            if not session_name: return

            client = TelegramClient(session_name, api_id, api_hash)
            client_holder["client"] = client
            await client.connect()
            
            if await client.is_user_authorized():
                await show_dialogs(client)
            else:
                show_login_form(session_name.replace('.session',''))

        def register_new(e):
            show_login_form()
        
        page.add(ft.Column([
            ft.Text("Welcome to Telegram Client", size=24), 
            session_dropdown,
            ft.ElevatedButton("Login with Session", on_click=login_with_session, width=300),
            ft.Text("Or"),
            ft.ElevatedButton("Register a New Account", on_click=register_new, width=300)
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15))
        page.update()

    # --- Initial App Load ---
    show_welcome_view()

if __name__ == "__main__":
    ft.app(target=main)
