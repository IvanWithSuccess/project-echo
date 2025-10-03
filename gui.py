
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

    file_picker = ft.FilePicker(on_result=lambda e: selected_file_path.update() if e.files else None)
    page.overlay.append(file_picker)

    async def show_account_manager_view():
        status_text = ft.Text(value="", visible=False)
        account_list_view = ft.ListView(expand=True, spacing=1, padding=0)

        def get_selected_accounts():
            return [c.data for c in account_list_view.controls if c.content.controls[0].value]

        async def delete_accounts(accounts_to_delete):
            all_accounts = load_accounts()
            sessions_to_delete = {acc['session_name'] for acc in accounts_to_delete}
            all_accounts = [acc for acc in all_accounts if acc['session_name'] not in sessions_to_delete]
            save_accounts(all_accounts)
            for session_name in sessions_to_delete:
                for ext in ['.session', '.session-journal']:
                    if os.path.exists(session_name + ext):
                        os.remove(session_name + ext)
            await show_account_manager_view()

        async def delete_selected_clicked(e):
            selected = get_selected_accounts()
            if selected:
                await delete_accounts(selected)

        async def assign_tags_clicked(e):
            selected = get_selected_accounts()
            if not selected:
                return

            tags_field = ft.TextField(label="Tags to add (comma-separated)")
            async def save_tags(e_save):
                new_tags = {tag.strip() for tag in tags_field.value.split(',') if tag.strip()}
                all_accounts = load_accounts()
                selected_names = {acc['session_name'] for acc in selected}
                for acc in all_accounts:
                    if acc['session_name'] in selected_names:
                        acc_tags = set(acc.get('tags', []))
                        acc_tags.update(new_tags)
                        acc['tags'] = sorted(list(acc_tags))
                save_accounts(all_accounts)
                page.dialog.open = False
                await show_account_manager_view()

            page.dialog = ft.AlertDialog(
                modal=True, title=ft.Text(f"Assign Tags to {len(selected)} Accounts"),
                content=tags_field,
                actions=[ft.TextButton("Save", on_click=save_tags), ft.TextButton("Cancel", on_click=lambda _: setattr(page.dialog, 'open', False) or page.update())])
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
                for i, account in enumerate(all_accounts):
                    if account['session_name'] == acc['session_name']:
                        all_accounts[i]['phone'] = phone_field.value
                        all_accounts[i]['notes'] = notes_field.value
                        all_accounts[i]['tags'] = [tag.strip() for tag in tags_field.value.split(',') if tag.strip()]
                        all_accounts[i]['proxy'] = proxy_field.value
                        break
                save_accounts(all_accounts)
                page.dialog.open = False
                await show_account_manager_view()

            page.dialog = ft.AlertDialog(
                modal=True, title=ft.Text(f"Settings for {acc.get('phone', acc['session_name'])}"),
                content=ft.Column([phone_field, notes_field, tags_field, proxy_field]),
                actions=[ft.TextButton("Save", on_click=save_settings), ft.TextButton("Cancel", on_click=lambda _: setattr(page.dialog, 'open', False) or page.update())])
            page.dialog.open = True
            page.update()

        async def login_and_show_dialogs(e):
            client = await get_client(e.control.data['session_name'])
            if client:
                await show_dialogs_view(client)

        async def check_all_accounts_status(e):
            check_btn = e.control
            check_btn.disabled = True
            status_text.value = "Checking all accounts..."
            status_text.visible = True
            page.update()

            all_accounts = load_accounts()
            for i, acc_container in enumerate(account_list_view.controls):
                acc = acc_container.data
                status_indicator = acc_container.content.controls[1].controls[0]
                status_text.value = f"Checking {acc.get('phone', acc['session_name'])}..."
                status_text.update()

                client = await get_client(acc['session_name'])
                if client:
                    all_accounts[i]['status'] = 'valid'
                    status_indicator.color = 'green'
                    await disconnect_client(acc['session_name'])
                else:
                    all_accounts[i]['status'] = 'invalid'
                    status_indicator.color = 'red'

                status_indicator.update()
                save_accounts(all_accounts) # Save after each check

            status_text.value = "All accounts checked."
            check_btn.disabled = False
            page.update()

        def build_account_list():
            accounts = load_accounts()
            status_colors = {"unknown": "grey", "valid": "green", "invalid": "red", "error": "orange"}
            account_list_view.controls.clear()
            for acc in accounts:
                account_list_view.controls.append(ft.Container(
                    data=acc,
                    content=ft.Row(vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                        ft.Checkbox(width=20),
                        ft.Row([ft.Icon(name="circle", color=status_colors.get(acc.get('status', 'unknown')), size=12)], width=30),
                        ft.VerticalDivider(),
                        ft.Column([
                            ft.Text(acc.get("phone", acc["session_name"]), weight=ft.FontWeight.BOLD),
                            ft.Text(acc.get("notes") or "No notes", italic=True, size=12, color="grey"),
                            ft.Row([ft.Chip(ft.Text(tag, size=10), bgcolor="blue_100", padding=4) for tag in acc.get("tags", [])], wrap=True, spacing=4, run_spacing=4)
                        ], spacing=2, expand=True),
                        ft.Row([
                            ft.ElevatedButton("Login", on_click=login_and_show_dialogs, data=acc),
                            ft.IconButton(icon="settings", on_click=open_settings_clicked, data=acc, tooltip="Settings"),
                            ft.IconButton(icon="delete_forever", icon_color="red", on_click=lambda e, acc_data=acc: delete_accounts([acc_data]), tooltip="Delete Account Permanently")
                        ], spacing=5)
                    ]),
                    padding=10, border=ft.border.only(bottom=ft.BorderSide(1, "whitesmoke"))
                ))
            page.update()

        build_account_list()
        
        main_content_area.content = ft.Column([
            ft.Row([
                ft.Text("Accounts", size=24, weight=ft.FontWeight.BOLD),
                ft.Row([
                    ft.ElevatedButton("Check All Status", icon="sync", on_click=check_all_accounts_status),
                    ft.ElevatedButton("Add Account", icon="add", on_click=lambda _: show_login_form())
                ])
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([
                ft.Checkbox(label="Select All", on_change=lambda e: [setattr(c.content.controls[0], 'value', e.control.value) for c in account_list_view.controls] or account_list_view.update()),
                ft.ElevatedButton("Delete Selected", icon="delete", on_click=delete_selected_clicked, color="red"),
                ft.ElevatedButton("Assign Tags", icon="label", on_click=assign_tags_clicked)
            ], spacing=10),
            ft.Divider(height=2),
            account_list_view,
            status_text
        ], expand=True)
        page.update()
    
    async def show_login_form():
        # This function can remain largely the same as the last correct version
        phone_field = ft.TextField(label="Phone Number (+1234567890)")
        code_field = ft.TextField(label="Confirmation Code", visible=False)
        pw_field = ft.TextField(label="2FA Password", password=True, visible=False)
        status = ft.Text()
        signin_button = ft.ElevatedButton("Get Code")
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
                        accounts.append({"session_name": session_name, "phone": phone, "status": "valid", "tags": [], "notes": "", "proxy": ""})
                        save_accounts(accounts)
                    await show_account_manager_view()
                    return
            except Exception as ex:
                status.value = f"Error: {ex}"
            finally:
                if temp_client.is_connected():
                    await temp_client.disconnect()
            page.update()

        signin_button.on_click = get_code_or_signin
        main_content_area.content = ft.Column([
            ft.Row([ft.ElevatedButton("Back", on_click=lambda _: show_account_manager_view())]),
            ft.Text("Add New Account", size=24),
            phone_field, code_field, pw_field, signin_button, status
        ])
        page.update()

    async def show_dialogs_view(client):
        # This function can remain largely the same
        async def go_back(e):
            await disconnect_client(client.session.string)
            await show_account_manager_view()

        dialogs_list_view = ft.ListView(expand=True, spacing=10)
        main_content_area.content = ft.Column([
            ft.Row([ft.Text("Your Chats", size=24), ft.ElevatedButton("Logout & Back", on_click=go_back)]),
            dialogs_list_view
        ], expand=True)
        page.update()
        
        async for dialog in client.iter_dialogs():
            dialogs_list_view.controls.append(ft.ListTile(title=ft.Text(dialog.name)))
        page.update()

    async def show_ad_cabinet_view():
        # This function can remain largely the same
        main_content_area.content = ft.Text("Ad Cabinet - To be implemented", size=24)
        page.update()

    rail = ft.NavigationRail(
        selected_index=0,
        on_change=lambda e: asyncio.create_task(show_account_manager_view() if e.control.selected_index == 0 else show_ad_cabinet_view()),
        destinations=[
            ft.NavigationRailDestination(icon="person_outline", selected_icon="person", label="Accounts"),
            ft.NavigationRailDestination(icon="campaign_outline", selected_icon="campaign", label="Ad Cabinet"),
        ]
    )

    page.add(ft.Row([rail, ft.VerticalDivider(width=1), main_content_area], expand=True))
    await show_account_manager_view()

if __name__ == "__main__":
    ft.app(target=main)
