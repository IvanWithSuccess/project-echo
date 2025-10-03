
import flet as ft
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
import asyncio
import os
import random

# Replace with your actual API ID and Hash
api_id = 26947469
api_hash = '731a222f9dd8b290db925a6a382159dd'

async def main(page: ft.Page):
    page.title = "Telegram Client"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    # Create directories for downloads if they don't exist
    if not os.path.exists("downloads/avatars"):
        os.makedirs("downloads/avatars")

    client_holder = {"client": None}
    handler_holder = {"dialog_handler": None}

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

    async def show_chat_messages(client: TelegramClient, chat_id: int, chat_name: str):
        page.clean()
        page.title = f"Chat: {chat_name}"

        messages_list_view = ft.ListView(expand=True, spacing=10, auto_scroll=True)
        chat_message_handler = None

        async def on_new_message(event):
            sender = await event.get_sender()
            sender_name = sender.first_name if hasattr(sender, 'first_name') else "Unknown"

            if event.photo:
                temp_msg = ft.Text(f"{sender_name}: [Downloading photo...]")
                messages_list_view.controls.append(temp_msg)
                page.update()
                file_path = await client.download_media(event.photo, file="downloads/")
                messages_list_view.controls.remove(temp_msg)
                messages_list_view.controls.append(ft.Column([ft.Text(sender_name), ft.Image(src=file_path, height=200)]))
            elif event.text:
                messages_list_view.controls.append(ft.Text(f"{sender_name}: {event.text}"))
            
            messages_list_view.scroll_to(offset=-1, duration=300)
            page.update()

        chat_message_handler = on_new_message
        client.add_event_handler(chat_message_handler, events.NewMessage(chats=chat_id, incoming=True))

        async def send_file_result(e: ft.FilePickerResultEvent):
            if e.files:
                picked_file_path = e.files[0].path
                messages_list_view.controls.append(ft.Column([ft.Text("You:"), ft.Image(src=picked_file_path, height=200)]))
                messages_list_view.scroll_to(offset=-1, duration=300)
                page.update()
                await client.send_file(chat_id, picked_file_path)
                await client.send_read_acknowledge(chat_id)
        
        file_picker = ft.FilePicker(on_result=send_file_result)
        page.overlay.append(file_picker)

        async def go_back(e):
            client.remove_event_handler(chat_message_handler)
            page.overlay.remove(file_picker)
            await show_dialogs(client)

        back_button = ft.ElevatedButton("Back to Chats", on_click=go_back)
        message_input = ft.TextField(hint_text="Type a message...", expand=True)

        async def send_message_click(e):
            if message_input.value:
                text = message_input.value
                messages_list_view.controls.append(ft.Text(f"You: {text}"))
                messages_list_view.scroll_to(offset=-1, duration=300)
                message_input.value = ""
                page.update()
                await client.send_message(chat_id, text)
                await client.send_read_acknowledge(chat_id)

        send_button = ft.IconButton(icon="send_rounded", on_click=send_message_click)
        attach_button = ft.IconButton(icon="attach_file", on_click=lambda _: file_picker.pick_files(allow_multiple=False, allowed_extensions=["jpg", "jpeg", "png", "gif"]))

        page.add(ft.Row([back_button]), ft.Text(f"Messages for {chat_name}", size=20, weight=ft.FontWeight.BOLD), messages_list_view, ft.Row([attach_button, message_input, send_button]))
        page.update()

        try:
            messages = []
            async for message in client.iter_messages(chat_id, limit=50):
                sender = await message.get_sender()
                sender_name = "You" if message.out else (sender.first_name if hasattr(sender, 'first_name') else "Unknown")
                if message.photo:
                    file_path = await client.download_media(message.photo, file="downloads/")
                    messages.append(ft.Column([ft.Text(sender_name), ft.Image(src=file_path, height=200)]))
                elif message.text:
                    messages.append(ft.Text(f"{sender_name}: {message.text}"))
            messages.reverse()
            messages_list_view.controls.extend(messages)
        except Exception as e:
            messages_list_view.controls.append(ft.Text(f"Error loading messages: {e}"))
        page.update()

    async def show_dialogs(client: TelegramClient):
        page.clean()
        page.title = "My Chats"
        dialogs_list_view = ft.ListView(expand=1, spacing=10)
        status_text = ft.Text("Loading chats...")
        
        colors_for_avatars = ["blue_200", "green_200", "red_200", "purple_200", "orange_200", "pink_200"]

        async def logout_and_cleanup(e):
            if handler_holder.get("dialog_handler"):
                client.remove_event_handler(handler_holder["dialog_handler"])
                handler_holder["dialog_handler"] = None
            session_filename = client.session.filename
            await client.log_out()
            client_holder["client"] = None
            if os.path.exists(session_filename):
                os.remove(session_filename)
            show_welcome_view()

        async def load_and_display_dialogs():
            dialogs_list_view.controls.clear()
            status_text.visible = True
            page.update()
            try:
                async for dialog in client.iter_dialogs():
                    avatar_path = await client.download_profile_photo(dialog.entity, file=f"downloads/avatars/{dialog.id}.jpg")
                    
                    leading_avatar = None
                    if avatar_path:
                        leading_avatar = ft.CircleAvatar(background_image_url=avatar_path)
                    else:
                        initials = "".join([p[0] for p in dialog.name.split()[:2]]).upper()
                        leading_avatar = ft.CircleAvatar(content=ft.Text(initials), bgcolor=random.choice(colors_for_avatars))

                    subtitle_text = ""
                    if dialog.message:
                        if dialog.message.photo:
                            subtitle_text = "[Photo]"
                        elif dialog.message.text:
                            subtitle_text = dialog.message.text
                        else:
                            subtitle_text = "[Media or service message]"
                        if dialog.message.out:
                            subtitle_text = f"You: {subtitle_text}"

                    trailing_widget = None
                    if dialog.unread_count > 0:
                        trailing_widget = ft.CircleAvatar(content=ft.Text(str(dialog.unread_count), color="white"), bgcolor="blue400", radius=14)
                    
                    dialogs_list_view.controls.append(ft.ListTile(
                        leading=leading_avatar,
                        title=ft.Text(dialog.name, weight=ft.FontWeight.BOLD),
                        subtitle=ft.Text(subtitle_text, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, size=14),
                        trailing=trailing_widget, data=dialog.id, on_click=on_chat_click))
                status_text.visible = False
            except Exception as e:
                status_text.value = f"Error loading chats: {e}"
            page.update()

        async def on_dialog_update(event):
            await load_and_display_dialogs()

        handler_holder["dialog_handler"] = on_dialog_update

        async def on_chat_click(e):
            if handler_holder.get("dialog_handler"):
                client.remove_event_handler(handler_holder["dialog_handler"])
                handler_holder["dialog_handler"] = None
            await client.send_read_acknowledge(e.control.data)
            await show_chat_messages(client, e.control.data, e.control.title.value)

        page.add(ft.Row([ft.Text("Your Chats", size=24, weight=ft.FontWeight.BOLD), ft.ElevatedButton("Logout", on_click=logout_and_cleanup, bgcolor="red_200")], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), status_text, dialogs_list_view)
        client.add_event_handler(on_dialog_update, events.Raw)
        await load_and_display_dialogs()

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
        page.add(ft.Column([ft.Text("Account Registration", size=24), session_name_field, phone_number_field, code_field, password_field, action_button, status_text], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20))
        page.update()

    show_welcome_view()

if __name__ == "__main__":
    ft.app(target=main)
