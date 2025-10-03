
import flet as ft
from telethon import TelegramClient, events
from telethon.tl.types import SendMessageTypingAction
from telethon.errors import SessionPasswordNeededError
import asyncio
import os
import random
import json

# Replace with your actual API ID and Hash
api_id = 26947469
api_hash = '731a222f9dd8b290db925a6a382159dd'
ACCOUNTS_FILE = "accounts.json"

# --- Data Persistence --- #
def load_accounts():
    if not os.path.exists(ACCOUNTS_FILE):
        return []
    with open(ACCOUNTS_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_accounts(accounts):
    with open(ACCOUNTS_FILE, 'w') as f:
        json.dump(accounts, f, indent=4)

# --- Main Application Logic --- #
async def main(page: ft.Page):
    page.title = "Telegram Marketing Tool"
    page.vertical_alignment = ft.MainAxisAlignment.START

    if not os.path.exists("downloads/avatars"):
        os.makedirs("downloads/avatars")

    client_holder = {"client": None}

    # --- Views --- #
    async def show_account_manager():
        page.clean()
        page.title = "Account Manager"
        accounts = load_accounts()
        account_list_view = ft.ListView(expand=True, spacing=10)

        async def login_and_show_dialogs(account):
            session_name = account['session_name']
            client = TelegramClient(session_name, api_id, api_hash)
            client_holder["client"] = client
            status_text.value = f"Connecting with {account.get('phone', session_name)}..."
            page.update()
            try:
                await client.connect()
                if await client.is_user_authorized():
                    await show_dialogs(client)
                else:
                    status_text.value = f"Session for {session_name} is invalid. Please re-add."
                    page.update()
            except Exception as e:
                status_text.value = f"Failed to connect: {e}"
                page.update()

        async def login_button_clicked(e):
            account = e.control.data
            await login_and_show_dialogs(account)

        for acc in accounts:
            login_button = ft.ElevatedButton("Login", on_click=login_button_clicked, data=acc)
            account_list_view.controls.append(
                ft.ListTile(
                    leading=ft.Icon(ft.icons.PERSON),
                    title=ft.Text(acc.get("phone", acc["session_name"])),
                    subtitle=ft.Text(f"Status: {acc.get('status', 'unknown')}"),
                    trailing=login_button
                )
            )
        
        status_text = ft.Text()
        
        async def add_account_clicked(e):
            await show_login_form()

        page.add(
            ft.Row(
                [
                    ft.Text("Accounts", size=24, weight=ft.FontWeight.BOLD),
                    ft.ElevatedButton("Add Account", icon="add", on_click=add_account_clicked),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            ),
            ft.Divider(),
            account_list_view,
            status_text
        )
        page.update()

    async def show_login_form():
        page.clean()
        page.title = "Add New Account"
        phone_number_field = ft.TextField(label="Phone Number (+1234567890)", width=300)
        code_field = ft.TextField(label="Confirmation Code", width=300, visible=False)
        password_field = ft.TextField(label="2FA Password", password=True, width=300, visible=False)
        action_button = ft.ElevatedButton(text="Get Code", width=300)
        status_text = ft.Text()

        async def button_click_handler(e):
            btn_text = e.control.text
            phone = phone_number_field.value.strip()
            session_name = phone.replace('+', '')
            client = client_holder.get("client")
            
            try:
                if btn_text == "Get Code":
                    if not phone:
                        status_text.value = "Phone number is required."
                        page.update()
                        return
                    
                    client = TelegramClient(session_name, api_id, api_hash)
                    client_holder["client"] = client
                    await client.connect()
                    await client.send_code_request(phone)

                    phone_number_field.disabled = True
                    code_field.visible = True
                    action_button.text = "Sign In"
                    status_text.value = "Code sent. Please check Telegram."

                elif btn_text in ["Sign In", "Sign In with Password"]:
                    if not client: return

                    if password_field.visible:
                        await client.sign_in(password=password_field.value.strip())
                    else:
                        await client.sign_in(phone, code_field.value.strip())
                    
                    accounts = load_accounts()
                    if not any(a['session_name'] == session_name for a in accounts):
                        accounts.append({
                            "session_name": session_name,
                            "phone": phone,
                            "status": "active"
                        })
                        save_accounts(accounts)

                    await show_account_manager()

            except SessionPasswordNeededError:
                password_field.visible = True
                action_button.text = "Sign In with Password"
                status_text.value = "2FA enabled. Please enter your password."
            except Exception as ex:
                status_text.value = f"Error: {ex}"
            page.update()

        action_button.on_click = button_click_handler
        
        async def go_to_manager(e):
            await show_account_manager()

        back_button = ft.ElevatedButton("Back to Manager", on_click=go_to_manager)

        page.add(ft.Column([
            ft.Row([back_button]),
            ft.Text("Add Account", size=24),
            phone_number_field, code_field, password_field, action_button, status_text
        ], alignment=ft.MainAxisAlignment.START, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20))
        page.update()

    async def show_dialogs(client: TelegramClient):
        page.clean()
        page.title = "My Chats"
        dialogs_list_view = ft.ListView(expand=1, spacing=10)
        status_text = ft.Text("Loading chats...")
        
        async def disconnect_and_go_to_manager(e):
            if client and client.is_connected():
                await client.disconnect()
            client_holder["client"] = None
            await show_account_manager()

        async def update_avatar(dialog, list_tile):
            relative_path = await client.download_profile_photo(dialog.entity, file=f"downloads/avatars/{dialog.id}.jpg")
            if relative_path:
                list_tile.leading.background_image_src = os.path.abspath(relative_path)
                page.update()

        async def on_chat_click(e):
            await show_chat_messages(client, e.control.data, e.control.title.value)

        async def load_and_display_dialogs():
            new_controls = []
            status_text.visible = True
            page.update()
            try:
                async for dialog in client.iter_dialogs():
                    initials = "".join([p[0] for p in dialog.name.split()[:2]]).upper()
                    leading_avatar = ft.CircleAvatar(content=ft.Text(initials))

                    subtitle_text = ""
                    if dialog.message:
                        if dialog.message.photo: subtitle_text = "[Photo]"
                        elif dialog.message.text: subtitle_text = dialog.message.text
                        else: subtitle_text = "[Media]"
                        if dialog.message.out: subtitle_text = f"You: {subtitle_text}"
                    
                    list_tile = ft.ListTile(
                        leading=leading_avatar, title=ft.Text(dialog.name, weight=ft.FontWeight.BOLD),
                        subtitle=ft.Text(subtitle_text, max_lines=1),
                        data=dialog.id, on_click=on_chat_click)
                    
                    new_controls.append(list_tile)
                    asyncio.create_task(update_avatar(dialog, list_tile))

                dialogs_list_view.controls = new_controls
                status_text.visible = False
            except Exception as e: status_text.value = f"Error: {e}"
            page.update()

        page.add(
            ft.Row(
                [ft.Text("Your Chats", size=24, weight=ft.FontWeight.BOLD), 
                 ft.ElevatedButton("Back to Manager", on_click=disconnect_and_go_to_manager, bgcolor="red_200")],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            ),
            status_text, dialogs_list_view)
        
        await load_and_display_dialogs()
    
    async def show_chat_messages(client: TelegramClient, chat_id: int, chat_name: str):
        page.clean()
        page.title = f"Chat: {chat_name}"
        messages_list_view = ft.ListView(expand=True, spacing=10, auto_scroll=True)
        typing_indicator = ft.Text("", italic=True, size=12)
        
        message_handler = None
        typing_handler = None

        async def on_new_message(event):
            sender = await event.get_sender()
            sender_name = sender.first_name if hasattr(sender, 'first_name') else "Unknown"
            messages_list_view.controls.append(ft.Text(f"{sender_name}: {event.text}"))
            page.update()

        async def on_typing(event):
            user = await event.get_user()
            name = user.first_name if user and user.first_name else "Someone"
            typing_indicator.value = f"{name} is typing..."
            page.update()
            await asyncio.sleep(2) # Show indicator for a bit
            typing_indicator.value = ""
            page.update()

        async def go_back(e):
            if message_handler: client.remove_event_handler(message_handler)
            if typing_handler: client.remove_event_handler(typing_handler)
            await show_dialogs(client)

        back_button = ft.ElevatedButton("Back to Chats", on_click=go_back)
        message_input = ft.TextField(hint_text="Type a message...", expand=True)

        async def send_message_click(e):
            if message_input.value:
                await client.send_message(chat_id, message_input.value)
                messages_list_view.controls.append(ft.Text(f"You: {message_input.value}"))
                message_input.value = ""
                messages_list_view.scroll_to(offset=-1, duration=300)
                page.update()

        send_button = ft.IconButton(icon="send_rounded", on_click=send_message_click)
        page.add(ft.Row([back_button]), messages_list_view, typing_indicator, ft.Row([message_input, send_button]))
        
        # Add handlers
        message_handler = client.add_event_handler(on_new_message, events.NewMessage(chats=chat_id, incoming=True))
        typing_handler = client.add_event_handler(on_typing, events.UserTyping(chats=chat_id))

        # Load initial messages
        messages = []
        async for message in client.iter_messages(chat_id, limit=30):
            sender = await message.get_sender()
            sender_name = "You" if message.out else (sender.first_name or "Unknown")
            messages.append(ft.Text(f"{sender_name}: {message.text}"))
        messages.reverse()
        messages_list_view.controls.extend(messages)
        page.update()

    # --- Initial View --- #
    await show_account_manager()

if __name__ == "__main__":
    ft.app(target=main)
