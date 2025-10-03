
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
    lock = client_locks.get(session_name)
    if not lock:
        lock = asyncio.Lock()
        client_locks[session_name] = lock

    async with lock:
        client = active_clients.get(session_name)
        try:
            if client and client.is_connected() and await client.is_user_authorized():
                logging.info(f"Reusing existing client for {session_name}")
                return client
        except Exception as e:
            logging.warning(f"Error with existing client for {session_name}: {e}. Disconnecting.")
            if client: await client.disconnect()
            if session_name in active_clients: del active_clients[session_name]

        logging.info(f"Creating new client for {session_name}")
        client = TelegramClient(session_name, api_id, api_hash)
        try:
            await client.connect()
            if not await client.is_user_authorized():
                logging.warning(f"Auth failed for {session_name}. Session may be invalid.")
                await client.disconnect()
                return None
            active_clients[session_name] = client
            return client
        except Exception as e:
            logging.error(f"Failed to create and connect client for {session_name}: {e}")
            if client.is_connected(): await client.disconnect()
            return None

async def disconnect_client(session_name):
    lock = client_locks.get(session_name)
    if not lock:
        return
    async with lock:
        client = active_clients.pop(session_name, None)
        if client and client.is_connected():
            logging.info(f"Disconnecting client for {session_name}")
            await client.disconnect()

async def disconnect_all_clients():
    logging.info("Disconnecting all active clients...")
    sessions = list(active_clients.keys())
    tasks = [disconnect_client(s) for s in sessions]
    await asyncio.gather(*tasks)
    logging.info("All clients disconnected.")

# --- Data Persistence --- #
def load_accounts():
    if not os.path.exists(ACCOUNTS_FILE):
        return []
    try:
        with open(ACCOUNTS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError): 
        return []

def save_accounts(accounts):
    with open(ACCOUNTS_FILE, 'w') as f:
        json.dump(accounts, f, indent=4)

# --- Main Application --- #
async def main(page: ft.Page):
    logging.info("Application starting.")
    page.title = "Telegram Marketing Tool"
    page.window_prevent_close = True

    async def on_window_event(e):
        if e.data == "close":
            await disconnect_all_clients()
            page.window_destroy()

    page.on_window_event = on_window_event

    main_content_area = ft.Container(expand=True)
    selected_file_path = ft.Text()
    file_picker = ft.FilePicker(on_result=lambda e: selected_file_path.update())
    page.overlay.append(file_picker)

    async def update_view(new_view_content):
        main_content_area.content = new_view_content
        main_content_area.update()

    async def show_account_manager_view(status_message=""):
        status_text = ft.Text(status_message)
        account_list_view = ft.ListView(expand=True, spacing=1, padding=0)

        def get_selected_sessions():
            return [c.data['session_name'] for c in account_list_view.controls if c.content.controls[0].value]

        async def delete_single_account(account_to_delete):
            logging.info(f"Attempting to delete single account: {account_to_delete['session_name']}")
            all_accounts = load_accounts()
            accounts_to_keep = [acc for acc in all_accounts if acc['session_name'] != account_to_delete['session_name']]
            save_accounts(accounts_to_keep)
            
            session_file = f"{account_to_delete['session_name']}.session"
            if os.path.exists(session_file):
                os.remove(session_file)
                logging.info(f"Deleted session file: {session_file}")
            
            await show_account_manager_view(f"Deleted account: {account_to_delete.get('phone', account_to_delete['session_name'])}")

        async def delete_selected_clicked(e):
            sessions_to_delete = get_selected_sessions()
            if not sessions_to_delete:
                return
            all_accounts = load_accounts()
            accounts_to_keep = [acc for acc in all_accounts if acc['session_name'] not in sessions_to_delete]
            save_accounts(accounts_to_keep)
            for session in sessions_to_delete:
                if os.path.exists(f"{session}.session"): os.remove(f"{session}.session")
            await show_account_manager_view("Deleted selected accounts.")

        async def assign_tags_clicked(e):
            selected_sessions = get_selected_sessions()
            if not selected_sessions:
                return

            tags_field = ft.TextField(label="Tags (comma-separated)")
            async def save_tags(e_save):
                new_tags = {tag.strip() for tag in tags_field.value.split(',') if tag.strip()}
                logging.info(f"Assigning tags: {new_tags} to sessions: {selected_sessions}")
                all_accounts = load_accounts()
                for acc in all_accounts:
                    if acc['session_name'] in selected_sessions:
                        current_tags = set(acc.get('tags', []))
                        current_tags.update(new_tags)
                        acc['tags'] = sorted(list(current_tags))
                        logging.info(f"Updated tags for {acc['session_name']}: {acc['tags']}")
                save_accounts(all_accounts)
                page.dialog.open = False
                page.update()
                await show_account_manager_view("Tags assigned.")

            page.dialog = ft.AlertDialog(modal=True, title=ft.Text(f"Assign Tags to {len(selected_sessions)} Accounts"), content=tags_field, actions=[ft.TextButton("Save", on_click=save_tags), ft.TextButton("Cancel", on_click=lambda _: setattr(page.dialog, 'open', False) or page.update())])
            page.dialog.open = True
            page.update()

        async def open_settings_clicked(e):
            acc = e.control.data
            phone_field = ft.TextField(label="Display Name", value=acc.get("phone", acc["session_name"]))
            notes_field = ft.TextField(label="Notes", value=acc.get("notes", ""), multiline=True)
            tags_field = ft.TextField(label="Tags (comma-separated)", value=", ".join(acc.get("tags", [])))
            proxy_field = ft.TextField(label="Proxy", hint_text="socks5://user:pass@host:port", value=acc.get("proxy", ""))

            async def save_settings(e_save):
                all_accounts = load_accounts()
                for account in all_accounts:
                    if account['session_name'] == acc['session_name']:
                        account['phone'] = phone_field.value
                        account['notes'] = notes_field.value
                        account['tags'] = [tag.strip() for tag in tags_field.value.split(',') if tag.strip()]
                        account['proxy'] = proxy_field.value
                        break
                save_accounts(all_accounts)
                page.dialog.open = False
                page.update()
                await show_account_manager_view("Settings saved.")

            page.dialog = ft.AlertDialog(modal=True, title=ft.Text(f"Settings for {acc.get('phone')}"), content=ft.Column([phone_field, notes_field, tags_field, proxy_field]), actions=[ft.TextButton("Save", on_click=save_settings), ft.TextButton("Cancel", on_click=lambda _: setattr(page.dialog, 'open', False) or page.update())])
            page.dialog.open = True
            page.update()

        async def login_and_show_dialogs(e):
            client = await get_client(e.control.data['session_name'])
            if client:
                await show_dialogs_view(client)

        async def check_all_accounts_status(e):
            check_btn = e.control
            check_btn.disabled = True
            check_btn.update()
            all_accounts = load_accounts()
            for i, acc in enumerate(all_accounts):
                client = await get_client(acc['session_name'])
                if client:
                    all_accounts[i]['status'] = 'valid'
                    await disconnect_client(acc['session_name'])
                else:
                    all_accounts[i]['status'] = 'invalid'
            save_accounts(all_accounts)
            check_btn.disabled = False
            check_btn.update()
            await show_account_manager_view("Finished checking all accounts.")

        def build_account_list():
            accounts = load_accounts()
            status_colors = {"unknown": "grey", "valid": "green", "invalid": "red", "error": "orange"}
            account_list_view.controls.clear()
            for acc in accounts:
                account_list_view.controls.append(ft.Container(
                    data=acc,
                    content=ft.Row(vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                        ft.Checkbox(width=20),
                        ft.Icon(name="circle", color=status_colors.get(acc.get('status', 'unknown')), size=12),
                        ft.VerticalDivider(width=10),
                        ft.Column([
                            ft.Text(acc.get("phone", acc["session_name"]), weight=ft.FontWeight.BOLD),
                            ft.Text(acc.get("notes") or "No notes", italic=True, size=12, color="grey"),
                            ft.Row([ft.Chip(ft.Text(tag, size=10), bgcolor="blue_100", padding=4) for tag in acc.get("tags", [])], wrap=True, spacing=4, run_spacing=4)
                        ], spacing=2, expand=True),
                        ft.Row([
                            ft.ElevatedButton("Login", on_click=login_and_show_dialogs, data=acc),
                            ft.IconButton(icon="settings", on_click=open_settings_clicked, data=acc, tooltip="Settings"),
                            ft.IconButton(icon="delete_forever", icon_color="red", on_click=lambda e: asyncio.create_task(delete_single_account(e.control.data)), data=acc, tooltip="Delete Account Permanently")
                        ], spacing=5)
                    ]),
                    padding=10, border=ft.border.only(bottom=ft.BorderSide(1, "whitesmoke"))
                ))
        
        build_account_list()
        view = ft.Column([
            ft.Row([ft.Text("Accounts", size=24), ft.Row([ft.ElevatedButton("Check All Status", icon="sync", on_click=check_all_accounts_status), ft.ElevatedButton("Add Account", icon="add", on_click=lambda e: asyncio.create_task(show_login_form()))])], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([ft.Checkbox(label="Select All", on_change=lambda e: [setattr(c.content.controls[0], 'value', e.control.value) for c in account_list_view.controls] or account_list_view.update()), ft.ElevatedButton("Delete Selected", icon="delete", on_click=delete_selected_clicked), ft.ElevatedButton("Assign Tags", icon="label", on_click=assign_tags_clicked)], spacing=10),
            ft.Divider(height=2),
            account_list_view,
            status_text
        ], expand=True)
        await update_view(view)

    async def show_login_form():
        phone_field = ft.TextField(label="Phone Number (+1234567890)")
        code_field = ft.TextField(label="Confirmation Code", visible=False)
        pw_field = ft.TextField(label="2FA Password", password=True, visible=False)
        status = ft.Text()
        signin_button = ft.ElevatedButton("Get Code")
        phone_code_hash = None

        async def get_code_or_signin(e):
            nonlocal phone_code_hash
            phone = phone_field.value.strip()
            session_name = phone.replace('+', '')
            client = TelegramClient(session_name, api_id, api_hash)
            await client.connect()
            try:
                if not code_field.visible:
                    result = await client.send_code_request(phone)
                    phone_code_hash = result.phone_code_hash
                    phone_field.disabled = True
                    code_field.visible = True
                    signin_button.text = "Sign In"
                    status.value = "Code sent."
                else:
                    try:
                        await client.sign_in(phone, code_field.value.strip(), phone_code_hash=phone_code_hash)
                    except SessionPasswordNeededError:
                        await client.sign_in(password=pw_field.value.strip())
                    
                    accounts = load_accounts()
                    if not any(a['session_name'] == session_name for a in accounts):
                        accounts.append({"session_name": session_name, "phone": phone, "status": "valid", "tags": [], "notes": "", "proxy": ""})
                        save_accounts(accounts)
                    await show_account_manager_view(f"Successfully added {phone}")
                    return
            except Exception as ex:
                status.value = f"Error: {ex}"
            finally:
                if client.is_connected(): await client.disconnect()
            page.update()

        signin_button.on_click = get_code_or_signin
        view = ft.Column([ft.Row([ft.ElevatedButton("Back", on_click=lambda e: asyncio.create_task(show_account_manager_view()))]), ft.Text("Add New Account", size=24), phone_field, code_field, pw_field, signin_button, status])
        await update_view(view)

    async def show_dialogs_view(client):
        async def on_chat_click(e):
            await show_chat_messages_view(client, e.control.data['id'], e.control.data['name'])

        dialogs_list_view = ft.ListView(expand=True, spacing=10)
        view = ft.Column([
            ft.Row([ft.Text("Your Chats", size=24), ft.ElevatedButton("Logout & Back", on_click=lambda e: asyncio.create_task(disconnect_client(client.session.string) or show_account_manager_view()))]),
            dialogs_list_view
        ], expand=True)
        await update_view(view)

        async for dialog in client.iter_dialogs():
            dialogs_list_view.controls.append(ft.ListTile(title=ft.Text(dialog.name), data={'id': dialog.id, 'name': dialog.name}, on_click=on_chat_click))
        dialogs_list_view.update()

    async def show_chat_messages_view(client, chat_id, chat_name):
        messages_list_view = ft.ListView(expand=True, spacing=10, auto_scroll=True)
        message_input = ft.TextField(hint_text="Type a message...", expand=True)

        async def send_message_click(e):
            if message_input.value:
                await client.send_message(chat_id, message_input.value)
                message_input.value = ""
                await show_chat_messages_view(client, chat_id, chat_name)

        view = ft.Column([
            ft.Row([ft.ElevatedButton("Back to Chats", on_click=lambda e: asyncio.create_task(show_dialogs_view(client))), ft.Text(chat_name, size=20)]),
            messages_list_view,
            ft.Row([message_input, ft.IconButton(icon="send", on_click=send_message_click)])
        ], expand=True)
        await update_view(view)

        async for message in client.iter_messages(chat_id, limit=50):
            sender = "You" if message.out else (message.sender.first_name if message.sender else "Unknown")
            messages_list_view.controls.insert(0, ft.Text(f"{sender}: {message.text}"))
        messages_list_view.update()

    async def show_ad_cabinet_view():
        await update_view(ft.Text("Ad Cabinet - To be implemented", size=24))

    # --- Initial View --- #
    rail = ft.NavigationRail(
        selected_index=0,
        on_change=lambda e: asyncio.create_task(show_account_manager_view() if e.control.selected_index == 0 else show_ad_cabinet_view()),
        destinations=[
            ft.NavigationRailDestination(icon="person_outline", selected_icon="person", label="Accounts"),
            ft.NavigationRailDestination(icon="campaign_outline", selected_icon="campaign", label="Ad Cabinet"),
        ])
    page.add(ft.Row([rail, ft.VerticalDivider(width=1), main_content_area], expand=True))
    await show_account_manager_view()

if __name__ == "__main__":
    ft.app(target=main)
