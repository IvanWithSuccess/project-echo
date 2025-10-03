
import flet as ft
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
import asyncio
import os
import json

# Replace with your actual API ID and Hash
api_id = 26947469
api_hash = '731a222f9dd8b290db925a6a382159dd'
ACCOUNTS_FILE = "accounts.json"

# --- Data Persistence --- #
def load_accounts():
    if not os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE, 'w') as f:
            json.dump([], f)
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
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    if not os.path.exists("downloads/avatars"):
        os.makedirs("downloads/avatars")
    if not os.path.exists("downloads/media"):
        os.makedirs("downloads/media")

    client_holder = {"client": None, "handlers": {}}

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
            account_list_view.controls.append(
                ft.ListTile(
                    leading=ft.Icon("person"),
                    title=ft.Text(acc.get("phone", acc["session_name"])),
                    subtitle=ft.Text(f"Status: {acc.get('status', 'active')}"),
                    trailing=ft.ElevatedButton("Login", on_click=login_button_clicked, data=acc)
                )
            )
        
        status_text = ft.Text()
        
        async def add_account_clicked(e):
            await show_login_form()

        page.add(
            ft.Column(
                [
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
                ],
                expand=True
            )
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
                        status_text.value = "Phone number is required."; page.update(); return
                    
                    accounts = load_accounts()
                    if any(a['phone'] == phone for a in accounts):
                        status_text.value = "Account already exists."; page.update(); return

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
                        accounts.append({"session_name": session_name, "phone": phone, "status": "active"})
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

        page.add(ft.Column([
            ft.ElevatedButton("Back to Manager", on_click=go_to_manager),
            ft.Text("Add Account", size=24),
            phone_number_field, code_field, password_field, action_button, status_text
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20))
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
            if not client_holder["client"] or not client_holder["client"].is_connected(): return
            path = f"downloads/avatars/{dialog.id}.jpg"
            if not os.path.exists(path):
              relative_path = await client.download_profile_photo(dialog.entity, file=path)
            else:
              relative_path = path
            if relative_path:
                list_tile.leading.content = None # Remove initials
                list_tile.leading.background_image_src = os.path.abspath(relative_path)
                page.update()

        async def on_chat_click(e):
            await show_chat_messages(client, e.control.data['id'], e.control.data['name'])

        async def load_and_display_dialogs():
            new_controls = []
            status_text.visible = True; page.update()
            try:
                async for dialog in client.iter_dialogs():
                    initials = "".join([p[0] for p in dialog.name.split()[:2]]).upper()
                    leading_avatar = ft.CircleAvatar(content=ft.Text(initials))

                    subtitle_text = "[No messages]"
                    if dialog.message:
                        if dialog.message.photo: subtitle_text = "[Photo]"
                        elif dialog.message.text: subtitle_text = dialog.message.text
                        else: subtitle_text = "[Media]"
                        if dialog.message.out: subtitle_text = f"You: {subtitle_text}"

                    trailing_widget = None
                    if dialog.unread_count > 0:
                        trailing_widget = ft.CircleAvatar(content=ft.Text(str(dialog.unread_count)), bgcolor=ft.colors.BLUE_400, radius=12)
                    
                    list_tile = ft.ListTile(
                        leading=leading_avatar, 
                        title=ft.Text(dialog.name, weight=ft.FontWeight.BOLD),
                        subtitle=ft.Text(subtitle_text, max_lines=1),
                        trailing=trailing_widget,
                        data={'id': dialog.id, 'name': dialog.name},
                        on_click=on_chat_click)
                    
                    new_controls.append(list_tile)
                    asyncio.create_task(update_avatar(dialog, list_tile))

                dialogs_list_view.controls = new_controls
                status_text.visible = False
            except Exception as e: status_text.value = f"Error: {e}"
            page.update()

        page.add(
            ft.Row([ft.Text("Your Chats", size=24, weight=ft.FontWeight.BOLD), ft.ElevatedButton("Back to Manager", on_click=disconnect_and_go_to_manager)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            status_text, dialogs_list_view)
        await load_and_display_dialogs()
    
    async def show_chat_messages(client: TelegramClient, chat_id: int, chat_name: str):
        page.clean()
        page.title = f"Chat: {chat_name}"
        messages_list_view = ft.ListView(expand=True, spacing=10, auto_scroll=True)

        async def on_new_message(event):
            sender = await event.get_sender()
            sender_name = sender.first_name if hasattr(sender, 'first_name') else "Unknown"
            
            content_control = None
            if event.photo:
                temp_msg = ft.Text(f"{sender_name}: [Downloading photo...]")
                messages_list_view.controls.append(temp_msg); page.update()
                relative_path = await client.download_media(event.photo, file="downloads/media/")
                messages_list_view.controls.remove(temp_msg)
                content_control = ft.Image(src=os.path.abspath(relative_path), height=200)
            elif event.text:
                content_control = ft.Text(event.text)
            
            if content_control:
                messages_list_view.controls.append(ft.Column([ft.Text(sender_name, weight=ft.FontWeight.BOLD), content_control]))
            page.update()

        handler = client.add_event_handler(on_new_message, events.NewMessage(chats=chat_id, incoming=True))

        async def go_back(e):
            client.remove_event_handler(handler)
            await show_dialogs(client)

        async def send_file_result(e: ft.FilePickerResultEvent):
            if e.files:
                picked_file = e.files[0]
                await client.send_file(chat_id, picked_file.path)
                # Show sent image
                sent_image_col = ft.Column([
                    ft.Text("You:", weight=ft.FontWeight.BOLD),
                    ft.Image(src=picked_file.path, height=200)
                ], alignment=ft.CrossAxisAlignment.END)
                messages_list_view.controls.append(sent_image_col)
                page.update()

        file_picker = ft.FilePicker(on_result=send_file_result)
        page.overlay.append(file_picker)

        back_button = ft.ElevatedButton("Back to Chats", on_click=go_back)
        message_input = ft.TextField(hint_text="Type a message...", expand=True)

        async def send_message_click(e):
            if message_input.value:
                text = message_input.value
                await client.send_message(chat_id, text)
                messages_list_view.controls.append(ft.Text(f"You: {text}", text_align=ft.TextAlign.RIGHT))
                message_input.value = ""; page.update()

        send_button = ft.IconButton(icon="send", on_click=send_message_click)
        attach_button = ft.IconButton(icon="attach_file", on_click=lambda _: file_picker.pick_files(allow_multiple=False, allowed_extensions=["jpg", "jpeg", "png", "gif"]))

        page.add(back_button, messages_list_view, ft.Row([attach_button, message_input, send_button]))
        
        messages_to_add = []
        try:
            async for message in client.iter_messages(chat_id, limit=50):
                sender = await message.get_sender()
                sender_name = "You" if message.out else (sender.first_name if hasattr(sender, 'first_name') else "Unknown")
                
                content_control = None
                if message.photo:
                    path = f"downloads/media/{message.photo.id}.jpg"
                    if not os.path.exists(path):
                        path = await client.download_media(message, file=path)
                    content_control = ft.Image(src=os.path.abspath(path), height=200)
                elif message.text:
                    content_control = ft.Text(message.text)
                
                if content_control:
                    col = ft.Column([ft.Text(sender_name, weight=ft.FontWeight.BOLD), content_control])
                    if message.out:
                       col.alignment=ft.CrossAxisAlignment.END
                    messages_to_add.append(col)

            messages_list_view.controls.extend(reversed(messages_to_add))
        except Exception as e:
            messages_list_view.controls.append(ft.Text(f"Error loading: {e}"))
        
        page.update()

    # --- Initial View --- #
    await show_account_manager()

if __name__ == "__main__":
    ft.app(target=main)
