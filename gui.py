
import flet as ft
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, FloodWaitError
import asyncio
import os
import json
import logging
from datetime import datetime

# --- Logging Setup --- #
LOG_FILE = "app.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(funcName)s] - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

# --- Constants & Config --- #
api_id = 26947469
api_hash = '731a222f9dd8b290db925a6a382159dd'
ACCOUNTS_FILE = "accounts.json"

# --- Client Management --- #
active_clients = {}
client_locks = {}

async def get_client(session_name):
    if session_name not in client_locks:
        client_locks[session_name] = asyncio.Lock()

    async with client_locks[session_name]:
        client = active_clients.get(session_name)
        try:
            if client and client.is_connected() and await client.is_user_authorized():
                logging.info(f"Reusing existing client for {session_name}")
                return client
        except Exception as e:
            logging.warning(f"Error with existing client for {session_name}: {e}. Creating a new one.")
            if client and client.is_connected():
                await client.disconnect()

        logging.info(f"Creating new client for {session_name}")
        new_client = TelegramClient(session_name, api_id, api_hash)
        try:
            await new_client.connect()
            if not await new_client.is_user_authorized():
                logging.warning(f"Auth failed for {session_name}. Session might be invalid.")
                if new_client.is_connected():
                    await new_client.disconnect()
                return None
            active_clients[session_name] = new_client
            return new_client
        except Exception as e:
            logging.error(f"Failed to create and connect client for {session_name}: {e}")
            if new_client.is_connected():
                await new_client.disconnect()
            return None

async def disconnect_client(session_name):
    if session_name in client_locks:
        async with client_locks[session_name]:
            client = active_clients.pop(session_name, None)
            if client and client.is_connected():
                logging.info(f"Disconnecting client for {session_name}")
                await client.disconnect()

async def disconnect_all_clients():
    logging.info("Disconnecting all active clients...")
    sessions = list(active_clients.keys())
    await asyncio.gather(*[disconnect_client(s) for s in sessions])
    logging.info("All clients disconnected.")

# --- Data Persistence --- #
def load_accounts():
    if not os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE, 'w') as f: json.dump([], f)
        return []
    try:
        with open(ACCOUNTS_FILE, 'r') as f:
            accounts = json.load(f)
            for acc in accounts:
                if 'status' not in acc: acc['status'] = 'unknown'
            return accounts
    except (json.JSONDecodeError, FileNotFoundError): 
        return []

def save_accounts(accounts):
    with open(ACCOUNTS_FILE, 'w') as f:
        json.dump(accounts, f, indent=4)

# --- Main Application --- #
async def main(page: ft.Page):
    logging.info("Application starting.")
    page.title = "Telegram Marketing Tool"

    async def on_window_event(e):
        if e.data == "close":
            logging.info("Window close event received.")
            await disconnect_all_clients()
            page.window_destroy()
    page.window_prevent_close = True
    page.on_window_event = on_window_event

    main_content_area = ft.Container(expand=True)
    selected_file_path = ft.Text()

    def on_file_picker_result(e: ft.FilePickerResultEvent):
        if e.files:
            selected_file_path.value = e.files[0].path
            selected_file_path.update()

    file_picker = ft.FilePicker(on_result=on_file_picker_result)
    page.overlay.append(file_picker)
    page.update()

    async def show_account_manager_view():
        status_text = ft.Text()
        account_list_view = ft.ListView(expand=True, spacing=1, padding=0)

        def get_selected_accounts():
            selected = []
            for control in account_list_view.controls:
                if control.content.controls[0].value: # Checkbox is the first control
                    selected.append(control.data)
            return selected

        async def delete_accounts(accounts_to_delete):
            accounts = load_accounts()
            sessions_to_delete = {acc['session_name'] for acc in accounts_to_delete}
            accounts = [acc for acc in accounts if acc['session_name'] not in sessions_to_delete]
            save_accounts(accounts)

            for session_name in sessions_to_delete:
                for file_ext in ['.session', '.session-journal']:
                    try:
                        os.remove(f"{session_name}{file_ext}")
                        logging.info(f"Deleted {session_name}{file_ext}")
                    except FileNotFoundError:
                        pass
            await show_account_manager_view()

        async def delete_single_account_clicked(e):
            await delete_accounts([e.control.data])

        async def delete_selected_clicked(e):
            selected = get_selected_accounts()
            if selected:
                await delete_accounts(selected)
            else:
                status_text.value = "No accounts selected to delete."
                status_text.update()

        async def assign_tags_clicked(e):
            selected_accounts = get_selected_accounts()
            if not selected_accounts:
                status_text.value = "No accounts selected to assign tags."
                status_text.update()
                return

            tags_field = ft.TextField(label="Tags to add (comma-separated)")

            async def save_tags(e_save):
                new_tags_str = tags_field.value.strip()
                if not new_tags_str:
                    page.dialog.open = False
                    page.update()
                    return

                new_tags = {tag.strip() for tag in new_tags_str.split(',') if tag.strip()}
                all_accounts = load_accounts()
                selected_session_names = {acc['session_name'] for acc in selected_accounts}

                for acc in all_accounts:
                    if acc['session_name'] in selected_session_names:
                        if 'tags' not in acc or not isinstance(acc['tags'], list):
                            acc['tags'] = []
                        
                        existing_tags = set(acc['tags'])
                        existing_tags.update(new_tags)
                        acc['tags'] = sorted(list(existing_tags))

                save_accounts(all_accounts)
                logging.info(f"Assigned tags '{new_tags_str}' to {len(selected_accounts)} accounts.")
                page.dialog.open = False
                page.update()
                await show_account_manager_view()

            def close_dialog(e_close):
                page.dialog.open = False
                page.update()

            page.dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text(f"Assign Tags to {len(selected_accounts)} Accounts"),
                content=tags_field,
                actions=[
                    ft.TextButton("Save", on_click=save_tags),
                    ft.TextButton("Cancel", on_click=close_dialog)
                ],
            )
            page.dialog.open = True
            page.update()

        async def login_and_show_dialogs(e):
            account = e.control.data
            phone_display = account.get('phone', account['session_name'])
            status_text.value = f"Connecting with {phone_display}..."
            status_text.update()
            client = await get_client(account['session_name'])
            if client:
                logging.info(f"Successfully got client for {phone_display}")
                await show_dialogs_view(client)
            else:
                msg = f"Failed to connect with {phone_display}. Session may be invalid."
                status_text.value = msg
                status_text.update()

        async def check_all_accounts_status(e):
            check_btn = e.control
            check_btn.disabled = True
            check_btn.update()
            accounts_data = load_accounts()

            for i, acc_container in enumerate(account_list_view.controls):
                acc = acc_container.data
                phone_display = acc.get('phone', acc['session_name'])
                status_text.value = f"Checking {phone_display}..."
                status_text.update()
                
                status_indicator = acc_container.content.controls[1].controls[0]
                client_to_check = TelegramClient(acc['session_name'], api_id, api_hash)
                
                try:
                    await client_to_check.connect()
                    if await client_to_check.is_user_authorized():
                        acc['status'] = 'valid'
                        status_indicator.color = 'green'
                    else:
                        acc['status'] = 'invalid'
                        status_indicator.color = 'red'
                except Exception as ex:
                    logging.error(f"Error checking {phone_display}: {ex}")
                    acc['status'] = 'error'
                    status_indicator.color = 'orange'
                finally:
                    if client_to_check.is_connected():
                        await client_to_check.disconnect()
                
                status_indicator.update()
                for original_acc in accounts_data:
                    if original_acc['session_name'] == acc['session_name']:
                        original_acc['status'] = acc['status']
                        break
                save_accounts(accounts_data)
                await asyncio.sleep(0.1)

            status_text.value = "All accounts checked."
            status_text.update()
            check_btn.disabled = False
            check_btn.update()

        async def edit_account_clicked(e):
            account_to_edit = e.control.data
            notes_field = ft.TextField(label="Notes", value=account_to_edit.get("notes", ""), multiline=True)
            tags_field = ft.TextField(label="Tags (comma-separated)", value=", ".join(account_to_edit.get("tags", [])))

            async def save_data(e_save):
                all_accounts = load_accounts()
                for acc in all_accounts:
                    if acc['session_name'] == account_to_edit['session_name']:
                        acc['notes'] = notes_field.value
                        acc['tags'] = [tag.strip() for tag in tags_field.value.split(',') if tag.strip()]
                        break
                save_accounts(all_accounts)
                page.dialog.open = False
                page.update()
                await show_account_manager_view()

            def close_dialog(e_close):
                page.dialog.open = False
                page.update()

            page.dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text(f"Edit {account_to_edit.get('phone', account_to_edit['session_name'])}"),
                content=ft.Column([notes_field, tags_field]),
                actions=[ft.TextButton("Save", on_click=save_data), ft.TextButton("Cancel", on_click=close_dialog)],
            )
            page.dialog.open = True
            page.update()

        async def add_account_clicked(e):
            await show_login_form()

        def build_account_list():
            accounts = load_accounts()
            status_colors = {"unknown": "grey", "valid": "green", "invalid": "red", "error": "orange"}
            account_list_view.controls.clear()
            for acc in accounts:
                tags_row = ft.Row(wrap=True, spacing=4, run_spacing=4)
                for tag in acc.get("tags", []):
                    tags_row.controls.append(ft.Chip(ft.Text(tag, size=10), bgcolor="blue_100", padding=4))
                
                account_list_view.controls.append(ft.Container(
                    data=acc,
                    content=ft.Row(vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                        ft.Checkbox(),
                        ft.Row([ft.Icon(name="circle", color=status_colors.get(acc.get('status', 'unknown')), size=12)], width=20),
                        ft.VerticalDivider(),
                        ft.Column([
                            ft.Text(acc.get("phone", acc["session_name"]), weight=ft.FontWeight.BOLD),
                            ft.Text(acc.get("notes") or "No notes", italic=True, size=12, color="grey"),
                            tags_row
                        ], spacing=2, expand=True),
                        ft.Row([
                            ft.ElevatedButton("Login", on_click=login_and_show_dialogs, data=acc),
                            ft.IconButton(icon="edit_note", on_click=edit_account_clicked, data=acc, tooltip="Edit notes & tags"),
                            ft.IconButton(icon="delete_forever", icon_color="red", on_click=delete_single_account_clicked, data=acc, tooltip="Delete Account Permanently")
                        ], spacing=5)
                    ]),
                    padding=10, border=ft.border.only(bottom=ft.BorderSide(1, "whitesmoke"))
                ))

        build_account_list()
        
        def select_all_changed(e):
            for control in account_list_view.controls:
                control.content.controls[0].value = e.control.value
            account_list_view.update()

        main_content_area.content = ft.Column([
            ft.Row([
                ft.Text("Accounts", size=24, weight=ft.FontWeight.BOLD),
                ft.Row([
                    ft.ElevatedButton("Check All Status", icon="sync", on_click=check_all_accounts_status),
                    ft.ElevatedButton("Add Account", icon="add", on_click=add_account_clicked)
                ])
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Row([
                ft.Checkbox(label="Select All", on_change=select_all_changed),
                ft.ElevatedButton("Delete Selected", icon="delete", on_click=delete_selected_clicked, color="red"),
                ft.ElevatedButton("Assign Tags", icon="label", on_click=assign_tags_clicked)
            ], spacing=10),
            ft.Divider(height=2),
            account_list_view,
            status_text
        ], expand=True)
        main_content_area.update()

    async def show_login_form():
        phone_field = ft.TextField(label="Phone Number (+1234567890)", width=300)
        code_field = ft.TextField(label="Confirmation Code", width=300, visible=False)
        pw_field = ft.TextField(label="2FA Password", password=True, width=300, visible=False)
        status = ft.Text()
        signin_button = ft.ElevatedButton("Get Code", width=300)
        phone_code_hash_holder = {}

        async def get_code_or_signin(e):
            phone = phone_field.value.strip()
            session_name = phone.replace('+', '')
            temp_client = TelegramClient(session_name, api_id, api_hash)
            try:
                await temp_client.connect()
                if not code_field.visible:
                    result = await temp_client.send_code_request(phone)
                    phone_code_hash_holder['value'] = result.phone_code_hash
                    phone_field.disabled = True
                    code_field.visible = True
                    signin_button.text = "Sign In"
                    status.value = "Code sent. Please check Telegram."
                else:
                    if not await temp_client.is_user_authorized():
                        password = pw_field.value.strip()
                        try:
                            await temp_client.sign_in(phone, code_field.value.strip(), phone_code_hash=phone_code_hash_holder.get('value'))
                        except SessionPasswordNeededError:
                            if not password:
                                status.value = "2FA Password needed."
                                pw_field.visible = True
                                signin_button.text = "Sign In with Password"
                                page.update()
                                return
                            await temp_client.sign_in(password=password)

                    accounts = load_accounts()
                    if not any(a['session_name'] == session_name for a in accounts):
                        accounts.append({"session_name": session_name, "phone": phone, "notes": "", "tags": [], "status": "valid"})
                        save_accounts(accounts)
                    logging.info(f"Successfully signed in and added account: {phone}")
                    await show_account_manager_view()
                    return
            except Exception as ex:
                status.value = f"Error: {ex}"
                logging.error(f"Sign-in error for {phone}: {ex}")
            finally:
                if temp_client.is_connected():
                    await temp_client.disconnect()
                    logging.info("Temp client for login disconnected.")
            page.update()

        signin_button.on_click = get_code_or_signin
        main_content_area.content = ft.Column([
            ft.Row([ft.ElevatedButton("Back to Accounts", on_click=lambda e: show_account_manager_view())]),
            ft.Text("Add New Account", size=24),
            phone_field, code_field, pw_field, signin_button, status
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20)
        main_content_area.update()

    async def show_dialogs_view(client):
        async def disconnect_and_go_back(e):
            await disconnect_client(client.session.string)
            await show_account_manager_view()

        async def on_chat_click(e):
            chat_info = e.control.data
            await show_chat_messages_view(client, chat_info['id'], chat_info['name'])

        dialogs_list_view = ft.ListView(expand=True, spacing=10)
        main_content_area.content = ft.Column([
            ft.Row([
                ft.Text("Your Chats", size=24, weight=ft.FontWeight.BOLD),
                ft.ElevatedButton("Logout & Back", icon="logout", on_click=disconnect_and_go_back)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            dialogs_list_view
        ], expand=True)
        main_content_area.update()
        
        async for dialog in client.iter_dialogs():
            initials = "".join([p[0] for p in dialog.name.split()[:2]]).upper()
            dialogs_list_view.controls.append(ft.ListTile(
                leading=ft.CircleAvatar(content=ft.Text(initials)),
                title=ft.Text(dialog.name),
                data={'id': dialog.id, 'name': dialog.name},
                on_click=on_chat_click
            ))
        dialogs_list_view.update()

    async def show_chat_messages_view(client, chat_id, chat_name):
        messages_list_view = ft.ListView(expand=True, spacing=10, auto_scroll=True)

        async def go_back(e):
            await show_dialogs_view(client)

        message_input = ft.TextField(hint_text="Type a message...", expand=True)

        async def send_message_click(e):
            if message_input.value:
                await client.send_message(chat_id, message_input.value)
                message_input.value = ""
                await show_chat_messages_view(client, chat_id, chat_name) # Refresh messages

        main_content_area.content = ft.Column([
            ft.Row([
                ft.ElevatedButton("Back to Chats", on_click=go_back),
                ft.Text(chat_name, size=20, weight=ft.FontWeight.BOLD)
            ]),
            messages_list_view,
            ft.Row([message_input, ft.IconButton(icon="send", on_click=send_message_click)])
        ], expand=True)
        main_content_area.update()

        async for message in client.iter_messages(chat_id, limit=50):
            sender = "You" if message.out else (message.sender.first_name if message.sender else "Unknown")
            messages_list_view.controls.insert(0, ft.Text(f"{sender}: {message.text}"))
        messages_list_view.update()

    async def show_ad_cabinet_view():
        sender_checkboxes = [ft.Checkbox(label=acc.get('phone', acc['session_name']), data=acc) for acc in load_accounts() if acc.get('status') == 'valid']
        target_chats_field = ft.TextField(label="Target Chats (@username or invite link, one per line)", multiline=True, min_lines=3)
        message_box = ft.TextField(label="Your message (optional if media is selected)", multiline=True, min_lines=5)
        delay_slider = ft.Slider(min=1, max=60, divisions=59, label="{value}s delay", value=5)
        status_log = ft.ListView(expand=True, spacing=5, auto_scroll=True)

        def local_log(message):
            timestamp = datetime.now().strftime('%H:%M:%S')
            status_log.controls.append(ft.Text(f"[{timestamp}] {message}"))
            status_log.update()
            logging.info(message)

        async def start_sending_click(e):
            send_button = e.control
            send_button.disabled = True
            send_button.update()

            senders = [cb.data for cb in sender_checkboxes if cb.value]
            targets = [line.strip() for line in target_chats_field.value.splitlines() if line.strip()]
            message = message_box.value
            delay = int(delay_slider.value)
            media_path = selected_file_path.value

            if not all([senders, targets]) or (not message and not media_path):
                local_log("Error: Senders, targets, and a message or media file are required.")
                send_button.disabled = False
                send_button.update()
                return

            local_log("====== Ad campaign started (Concurrent Mode) ======")

            async def run_sender_task(sender_acc):
                phone_display = sender_acc.get('phone', sender_acc['session_name'])
                session_name = sender_acc['session_name']
                local_log(f"--- Task started for {phone_display}")
                client = await get_client(session_name)
                if not client:
                    local_log(f"    -> Auth failed for {phone_display}, skipping task.")
                    return

                for target in targets:
                    try:
                        local_log(f"    -> {phone_display} sending to {target}")
                        if media_path and os.path.exists(media_path):
                            await client.send_file(target, file=media_path, caption=message or '')
                        elif message:
                            await client.send_message(target, message)
                        local_log(f"    -> Sent successfully to {target}. Waiting {delay}s.")
                        await asyncio.sleep(delay)
                    except FloodWaitError as fwe:
                        local_log(f"    -> Flood wait for {fwe.seconds}s on {phone_display}. Sleeping.")
                        await asyncio.sleep(fwe.seconds)
                    except Exception as ex:
                        local_log(f"    -> Failed to send to {target} from {phone_display}: {ex}")
                local_log(f"--- Task finished for {phone_display} ---")

            tasks = [run_sender_task(sender) for sender in senders]
            await asyncio.gather(*tasks)

            local_log("====== All tasks finished ======")
            send_button.disabled = False
            send_button.update()

        main_content_area.content = ft.Column([
            ft.Text("Ad Cabinet", size=24, weight=ft.FontWeight.BOLD),
            ft.Text("1. Select accounts to send from (only valid accounts are shown):"),
            ft.Container(content=ft.Column(sender_checkboxes), border=ft.border.all(1, "black26"), padding=10, border_radius=5),
            ft.Text("2. Enter target chats (one per line):"),
            target_chats_field,
            ft.Text("3. Compose your message:"),
            message_box,
            ft.Row([ft.ElevatedButton("Select Media", icon="attach_file", on_click=lambda _: file_picker.pick_files()), selected_file_path]),
            ft.Text("4. Set delay between messages:"),
            delay_slider,
            ft.ElevatedButton("Start Sending", icon="rocket_launch", on_click=start_sending_click),
            ft.Divider(),
            ft.Text("Status Log:"),
            ft.Container(content=status_log, expand=True, border=ft.border.all(1, "black26"), padding=10, border_radius=5)
        ], expand=True, scroll=ft.ScrollMode.ADAPTIVE)
        main_content_area.update()

    async def nav_rail_changed(e):
        idx = e.control.selected_index
        if idx == 0: await show_account_manager_view()
        elif idx == 1: await show_ad_cabinet_view()

    rail = ft.NavigationRail(
        selected_index=0, label_type=ft.NavigationRailLabelType.ALL,
        min_width=100, min_extended_width=200,
        destinations=[
            ft.NavigationRailDestination(icon="person_outline", selected_icon="person", label="Accounts"),
            ft.NavigationRailDestination(icon="campaign_outline", selected_icon="campaign", label="Ad Cabinet"),
        ],
        on_change=nav_rail_changed,
    )

    page.add(ft.Row([rail, ft.VerticalDivider(width=1), main_content_area], expand=True))
    await show_account_manager_view()

if __name__ == "__main__":
    if not os.path.exists("downloads"): os.makedirs("downloads")
    ft.app(target=main)
