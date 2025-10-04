
import flet as ft
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, FloodWaitError
import asyncio
import os
import json
import logging
from datetime import datetime
from functools import partial

# --- Logging Setup --- #
LOG_FILE = "app.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(funcName)s] - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
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

async def get_client(session_name, proxy_info=None):
    lock = client_locks.get(session_name)
    if not lock:
        lock = asyncio.Lock()
        client_locks[session_name] = lock

    async with lock:
        if session_name in active_clients:
            client = active_clients[session_name]
            try:
                if client.is_connected() and await client.is_user_authorized():
                    logging.info(f"Reusing existing client for {session_name}")
                    return client
                else:
                    logging.info(f"Existing client for {session_name} is disconnected. Reconnecting.")
                    await client.disconnect() # Ensure clean state
            except Exception as e:
                logging.warning(f"Error with existing client for {session_name}: {e}. Forcing disconnect.")
                if client and client.is_connected():
                    await client.disconnect()

        logging.info(f"Creating new client for {session_name}")
        client = TelegramClient(session_name, api_id, api_hash, proxy=proxy_info)
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
            if client and client.is_connected():
                await client.disconnect()
            return None

async def disconnect_client(session_name):
    lock = client_locks.get(session_name)
    if not lock:
        logging.warning(f"No lock found for {session_name} on disconnect.")
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
        with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def save_accounts(accounts):
    with open(ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(accounts, f, indent=4, ensure_ascii=False)

# --- Main Application --- #
async def main(page: ft.Page):
    logging.info("Application starting.")
    page.title = "Telegram Marketing Tool"
    page.window_prevent_close = True
    page.views.clear()

    async def on_window_event(e):
        if e.data == "close":
            logging.info("Window close event triggered.")
            await disconnect_all_clients()
            page.window_destroy()

    page.on_window_event = on_window_event
    
    # --- File Picker --- #
    async def on_media_pick_result(e: ft.FilePickerResultEvent):
        if e.files:
            selected_media_path.value = e.files[0].path
            logging.info(f"Media file selected: {e.files[0].path}")
        else:
            selected_media_path.value = "Media file was not selected."
            logging.warning("Media file selection was cancelled.")
        selected_media_path.update()

    media_file_picker = ft.FilePicker(on_result=on_media_pick_result)
    page.overlay.append(media_file_picker)
    selected_media_path = ft.Text(value="", visible=True)

    # --- Core Navigation/View Management --- #
    async def change_view(view):
        page.views.clear()
        page.views.append(view)
        page.update()
        
    async def go_back(e):
        page.views.pop()
        top_view = page.views[-1]
        await build_account_manager_view_content(top_view.controls[0])
        page.update()

    # --- Ad Cabinet View --- #
    async def build_ad_cabinet_view():
        all_accounts = load_accounts()
        all_tags = sorted(list(set(tag for acc in all_accounts for tag in acc.get('tags', []))))

        sender_checkboxes = [ft.Checkbox(label=acc.get('phone', acc['session_name']), data=acc) for acc in all_accounts]
        
        tags_dropdown = ft.Dropdown(
            label="Filter by Tag",
            options=[ft.dropdown.Option(tag) for tag in all_tags],
        )

        def filter_senders_by_tag(e):
            selected_tag = e.control.value
            for cb in sender_checkboxes:
                cb.visible = selected_tag is None or selected_tag in cb.data.get('tags', [])
            ad_cabinet_content.update()

        tags_dropdown.on_change = filter_senders_by_tag

        targets_input = ft.TextField(label="Targets (@username or chat link)", multiline=True, min_lines=3, expand=True)
        message_input = ft.TextField(label="Message", multiline=True, min_lines=5, expand=True)
        delay_input = ft.TextField(label="Delay (seconds)", value="5", width=100)
        
        status_log = ft.ListView(expand=True, spacing=5, auto_scroll=True)

        async def run_campaign_click(e):
            # ... (campaign logic will be implemented here) ...
            status_log.controls.append(ft.Text("Campaign Started..."))
            status_log.update()
            
        ad_cabinet_content = ft.Column(
            [
                ft.Row([tags_dropdown, ft.Checkbox(label="Select all visible")]),
                ft.Text("Select Senders:"),
                ft.Column(sender_checkboxes, scroll=ft.ScrollMode.ADAPTIVE, height=150),
                ft.Divider(),
                ft.Row([targets_input]),
                ft.Row([message_input]),
                ft.Row(
                    [
                        ft.ElevatedButton("Select Media", icon="upload_file", on_click=lambda _: media_file_picker.pick_files(allow_multiple=False)),
                        selected_media_path,
                    ]
                ),
                ft.Row([delay_input, ft.ElevatedButton("Start Campaign", icon="send", on_click=run_campaign_click)]),
                ft.Divider(),
                ft.Text("Campaign Log:"),
                status_log,
            ],
            expand=True,
            scroll=ft.ScrollMode.ADAPTIVE
        )
        return ad_cabinet_content

    # --- Account Manager View --- #
    async def build_account_manager_view_content(container: ft.Container):
        
        account_list_view = ft.ListView(expand=True, spacing=0, padding=0)

        def get_selected_sessions():
            return [c.data['session_name'] for c in account_list_view.controls if c.content.controls[0].value]

        async def delete_single_account_click(acc_to_delete):
            logging.info(f"Attempting to delete single account: {acc_to_delete['session_name']}")
            all_accounts = load_accounts()
            accounts_to_keep = [acc for acc in all_accounts if acc['session_name'] != acc_to_delete['session_name']]
            save_accounts(accounts_to_keep)
            
            session_file = f"{acc_to_delete['session_name']}.session"
            if os.path.exists(session_file):
                os.remove(session_file)
                logging.info(f"Deleted session file: {session_file}")
            
            await build_account_manager_view_content(container)

        async def delete_selected_click(e):
            sessions_to_delete = get_selected_sessions()
            if not sessions_to_delete: return

            all_accounts = load_accounts()
            accounts_to_keep = [acc for acc in all_accounts if acc['session_name'] not in sessions_to_delete]
            save_accounts(accounts_to_keep)
            for session in sessions_to_delete:
                if os.path.exists(f"{session}.session"): os.remove(f"{session}.session")
            
            await build_account_manager_view_content(container)

        async def assign_tags_click(e):
            selected_sessions = get_selected_sessions()
            if not selected_sessions: return

            tags_field = ft.TextField(label="Tags (comma-separated)")
            
            async def save_tags_click(e_save):
                page.dialog.open = False
                page.update()
                new_tags = {tag.strip() for tag in tags_field.value.split(',') if tag.strip()}
                all_accounts = load_accounts()
                for acc in all_accounts:
                    if acc['session_name'] in selected_sessions:
                        current_tags = set(acc.get('tags', []))
                        current_tags.update(new_tags)
                        acc['tags'] = sorted(list(current_tags))
                save_accounts(all_accounts)
                await build_account_manager_view_content(container)

            page.dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text(f"Assign Tags to {len(selected_sessions)} Accounts"),
                content=tags_field,
                actions=[
                    ft.TextButton("Save", on_click=lambda e: asyncio.create_task(save_tags_click(e))),
                    ft.TextButton("Cancel", on_click=lambda _: setattr(page.dialog, 'open', False) or page.update())
                ]
            )
            page.dialog.open = True
            page.update()

        async def open_settings_click(acc):
            phone_field = ft.TextField(label="Display Name", value=acc.get("phone", acc["session_name"]))
            notes_field = ft.TextField(label="Notes", value=acc.get("notes", ""), multiline=True)
            tags_field = ft.TextField(label="Tags (comma-separated)", value=", ".join(acc.get("tags", [])))
            proxy_field = ft.TextField(label="Proxy", hint_text="socks5://user:pass@host:port", value=acc.get("proxy", ""))

            async def save_settings_click(e_save):
                page.dialog.open = False
                page.update()
                all_accounts = load_accounts()
                for account in all_accounts:
                    if account['session_name'] == acc['session_name']:
                        account['phone'] = phone_field.value
                        account['notes'] = notes_field.value
                        account['tags'] = [tag.strip() for tag in tags_field.value.split(',') if tag.strip()]
                        account['proxy'] = proxy_field.value
                        break
                save_accounts(all_accounts)
                await build_account_manager_view_content(container)

            page.dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text(f"Settings for {acc.get('phone')}"),
                content=ft.Column([phone_field, notes_field, tags_field, proxy_field]),
                actions=[
                    ft.TextButton("Save", on_click=lambda e: asyncio.create_task(save_settings_click(e))),
                    ft.TextButton("Cancel", on_click=lambda _: setattr(page.dialog, 'open', False) or page.update())
                ]
            )
            page.dialog.open = True
            page.update()

        async def login_and_show_dialogs_click(acc):
            client = await get_client(acc['session_name'])
            if client:
                await build_dialogs_view(acc['session_name'])
        
        def build_account_list():
            accounts = load_accounts()
            status_colors = {"unknown": "grey", "valid": "green", "invalid": "red"}
            account_list_view.controls.clear()
            for acc in accounts:
                account_list_view.controls.append(
                    ft.Container(
                        data=acc,
                        content=ft.Row(
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Checkbox(width=20),
                                ft.Icon(name="circle", color=status_colors.get(acc.get('status', 'unknown')), size=12),
                                ft.VerticalDivider(width=5),
                                ft.Column([
                                    ft.Text(acc.get("phone", acc["session_name"]), weight=ft.FontWeight.BOLD),
                                    ft.Text(acc.get("notes") or "No notes", italic=True, size=11, color="grey"),
                                    ft.Row([ft.Chip(ft.Text(tag, size=10), bgcolor=ft.colors.with_opacity(0.1, "blue"), padding=4) for tag in acc.get("tags", [])],
                                           wrap=True, spacing=4, run_spacing=4)
                                ], spacing=2, expand=True),
                                ft.Row([
                                    ft.ElevatedButton("Login", on_click=partial(lambda a: asyncio.create_task(login_and_show_dialogs_click(a)), acc)),
                                    ft.IconButton(icon="settings", on_click=partial(lambda a: asyncio.create_task(open_settings_click(a)), acc), tooltip="Settings"),
                                    ft.IconButton(icon="delete_forever", icon_color="red", on_click=partial(lambda a: asyncio.create_task(delete_single_account_click(a)), acc), tooltip="Delete")
                                ], spacing=5)
                            ]
                        ),
                        padding=10,
                        border=ft.border.only(bottom=ft.BorderSide(1, "whitesmoke"))
                    )
                )

        build_account_list()
        
        container.content = ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("Accounts", size=24),
                        ft.Row([
                            ft.ElevatedButton("Add Account", icon="add", on_click=lambda _: asyncio.create_task(build_login_view()))
                        ])
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                ),
                ft.Row(
                    [
                        ft.Checkbox(label="Select All", on_change=lambda e: [setattr(c.content.controls[0], 'value', e.control.value) for c in account_list_view.controls] or account_list_view.update()),
                        ft.ElevatedButton("Delete Selected", icon="delete", on_click=delete_selected_click),
                        ft.ElevatedButton("Assign Tags", icon="label", on_click=assign_tags_click)
                    ],
                    spacing=10
                ),
                ft.Divider(height=2),
                account_list_view,
            ],
            expand=True
        )
        container.update()

    # --- Login View --- #
    async def build_login_view():
        phone_field = ft.TextField(label="Phone Number (+1234567890)", autofocus=True)
        code_field = ft.TextField(label="Confirmation Code", visible=False)
        pw_field = ft.TextField(label="2FA Password", password=True, visible=False)
        status = ft.Text()
        signin_button = ft.ElevatedButton("Get Code")
        
        temp_client = None
        phone_code_hash = None
        phone_number = None

        async def get_code_or_signin_click(e):
            nonlocal temp_client, phone_code_hash, phone_number
            
            signin_button.disabled = True
            signin_button.update()
            
            phone_number = phone_field.value.strip()
            session_name = phone_number.replace('+', '')

            try:
                if not code_field.visible: # First step: Get code
                    status.value = f"Connecting to send code to {phone_number}..."
                    status.update()
                    temp_client = TelegramClient(session_name, api_id, api_hash)
                    await temp_client.connect()
                    
                    result = await temp_client.send_code_request(phone_number)
                    phone_code_hash = result.phone_code_hash
                    
                    phone_field.disabled = True
                    code_field.visible = True
                    signin_button.text = "Sign In"
                    status.value = "Code sent. Please check your Telegram app."
                
                else: # Second step: Sign in
                    status.value = "Signing in..."
                    status.update()
                    try:
                        await temp_client.sign_in(phone_number, code_field.value.strip(), phone_code_hash=phone_code_hash)
                    except SessionPasswordNeededError:
                        pw_field.visible = True
                        signin_button.text = "Sign In with Password"
                        status.value = "2FA Password needed."
                        pw_field.update()
                        signin_button.disabled = False
                        signin_button.update()
                        return # Wait for user to enter password
                    except Exception as ex_signin:
                        status.value = f"Sign-in error: {ex_signin}"
                        status.update()
                        return

                    if pw_field.visible and pw_field.value:
                        try:
                           await temp_client.sign_in(password=pw_field.value.strip())
                        except Exception as ex_pw:
                            status.value = f"Password error: {ex_pw}"
                            status.update()
                            return
                    
                    # Save account
                    accounts = load_accounts()
                    if not any(a['session_name'] == session_name for a in accounts):
                        accounts.append({"session_name": session_name, "phone": phone_number, "status": "valid", "tags": [], "notes": "", "proxy": ""})
                        save_accounts(accounts)
                    
                    status.value = f"Successfully added {phone_number}!"
                    status.update()
                    await asyncio.sleep(1)
                    await go_back(None)

            except Exception as ex:
                status.value = f"An error occurred: {ex}"
            finally:
                if signin_button.text != "Sign In with Password":
                    if temp_client and temp_client.is_connected():
                        await temp_client.disconnect()
                signin_button.disabled = False
                page.update()

        signin_button.on_click = lambda e: asyncio.create_task(get_code_or_signin_click(e))

        login_view_content = ft.Column([
                ft.Text("Add New Account", size=24),
                phone_field,
                code_field,
                pw_field,
                signin_button,
                status
            ])
        
        view = ft.View(
            "/add_account",
            [
                ft.AppBar(title=ft.Text("Add Account"), leading=ft.IconButton(icon=ft.icons.ARROW_BACK, on_click=go_back)),
                login_view_content
            ],
            padding=20
        )
        await change_view(view)

    # --- Dialogs/Chats View --- #
    async def build_dialogs_view(session_name):
        client = await get_client(session_name)
        if not client:
            # Handle error... maybe show a snackbar
            return

        dialogs_list_view = ft.ListView(expand=True, spacing=5)
        
        async def on_chat_click(e):
            # Navigate to chat messages view
            pass

        async def logout_and_back_click(e):
            await disconnect_client(session_name)
            await go_back(e)

        view = ft.View(
            f"/{session_name}/dialogs",
            [
                ft.AppBar(
                    title=ft.Text(f"Chats for {session_name}"), 
                    leading=ft.IconButton(icon=ft.icons.ARROW_BACK, on_click=lambda e: asyncio.create_task(logout_and_back_click(e)))
                ),
                dialogs_list_view
            ],
            padding=10
        )
        
        page.views.append(view)
        page.update()

        try:
            async for dialog in client.iter_dialogs():
                dialogs_list_view.controls.append(ft.ListTile(title=ft.Text(dialog.name), data={'id': dialog.id, 'name': dialog.name}, on_click=on_chat_click))
            dialogs_list_view.update()
        except Exception as e:
            logging.error(f"Error fetching dialogs for {session_name}: {e}")


    # --- App Shell and Initial View --- #
    async def switch_main_view(e):
        idx = e.control.selected_index
        rail.selected_index = idx
        if idx == 0:
            app_content_area.content = await build_account_manager_view_content(app_content_area)
        elif idx == 1:
            app_content_area.content = await build_ad_cabinet_view()
        app_content_area.update()
        
    rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        on_change=lambda e: asyncio.create_task(switch_main_view(e)),
        destinations=[
            ft.NavigationRailDestination(icon="person_outline", selected_icon="person", label="Accounts"),
            ft.NavigationRailDestination(icon="campaign_outline", selected_icon="campaign", label="Ad Cabinet"),
        ],
        group_alignment=-0.9
    )

    app_content_area = ft.Container(expand=True)
    
    initial_view = ft.View(
        "/",
        [
            ft.Row(
                [
                    rail,
                    ft.VerticalDivider(width=1),
                    app_content_area,
                ],
                expand=True,
            )
        ]
    )
    
    await change_view(initial_view)
    await build_account_manager_view_content(app_content_area)


if __name__ == "__main__":
    ft.app(target=main)

