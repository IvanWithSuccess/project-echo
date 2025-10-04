
import flet as ft
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
import asyncio
import os
import json
import logging
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
    lock = client_locks.setdefault(session_name, asyncio.Lock())

    async with lock:
        if session_name in active_clients:
            client = active_clients[session_name]
            try:
                if client.is_connected() and await client.is_user_authorized():
                    logging.info(f"Reusing existing client for {session_name}")
                    return client
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
            if client and hasattr(client, 'is_connected') and client.is_connected():
                await client.disconnect()
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
    await asyncio.gather(*(disconnect_client(s) for s in sessions))
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

    async def on_window_event(e):
        if e.data == "close":
            await disconnect_all_clients()
            page.window_destroy()

    page.on_window_event = on_window_event
    page.views.clear()

    # --- Global Content Containers --- #
    app_content_area = ft.Container(expand=True)
    selected_media_path = ft.Text(value="", visible=True)

    # --- File Picker --- #
    async def on_media_pick_result(e: ft.FilePickerResultEvent):
        if e.files:
            selected_media_path.value = e.files[0].path
            logging.info(f"Media file selected: {e.files[0].path}")
        else:
            selected_media_path.value = "Media file was not selected."
        selected_media_path.update()

    media_file_picker = ft.FilePicker(on_result=on_media_pick_result)
    page.overlay.append(media_file_picker)

    # --- Navigation --- #
    async def go_to_view(view):
        page.views.append(view)
        page.update()

    async def go_back_and_rebuild(e):
        page.views.pop()
        # The view below is now the main view. We need to find its content area and rebuild it.
        main_view_content_area = page.views[0].controls[0].controls[2]
        await build_account_manager_content(main_view_content_area)
        page.update()

    # --- Ad Cabinet --- #
    async def build_ad_cabinet_content():
        # ... Omitted for brevity, assuming no changes needed here yet ...
        return ft.Column([ft.Text("Ad Cabinet", size=24), ft.ElevatedButton("Select Media", on_click=lambda _: media_file_picker.pick_files())])

    # --- Account Manager --- #
    async def build_account_manager_content(container: ft.Container):
        account_list_view = ft.ListView(expand=True, spacing=0, padding=0)

        def get_selected_sessions():
            return [c.data['session_name'] for c in account_list_view.controls if c.content.controls[0].value]

        async def delete_single_account(acc_to_delete):
            all_accounts = load_accounts()
            accounts_to_keep = [acc for acc in all_accounts if acc['session_name'] != acc_to_delete['session_name']]
            save_accounts(accounts_to_keep)
            if os.path.exists(f"{acc_to_delete['session_name']}.session"): os.remove(f"{acc_to_delete['session_name']}.session")
            await build_account_manager_content(container)

        async def delete_selected(e):
            sessions_to_delete = get_selected_sessions()
            if not sessions_to_delete: return
            all_accounts = load_accounts()
            accounts_to_keep = [acc for acc in all_accounts if acc['session_name'] not in sessions_to_delete]
            save_accounts(accounts_to_keep)
            for session in sessions_to_delete:
                if os.path.exists(f"{session}.session"): os.remove(f"{session}.session")
            await build_account_manager_content(container)

        async def assign_tags_dialog(e):
            selected_sessions = get_selected_sessions()
            if not selected_sessions: return
            tags_field = ft.TextField(label="Tags (comma-separated)")

            async def save_tags(e_save):
                page.dialog.open = False; page.update()
                new_tags = {tag.strip() for tag in tags_field.value.split(',') if tag.strip()}
                all_accounts = load_accounts()
                for acc in all_accounts:
                    if acc['session_name'] in selected_sessions:
                        acc['tags'] = sorted(list(set(acc.get('tags', [])).union(new_tags)))
                save_accounts(all_accounts)
                await build_account_manager_content(container)
            
            page.dialog = ft.AlertDialog(modal=True, title=ft.Text(f"Assign Tags"), content=tags_field, actions=[ft.TextButton("Save", on_click=lambda e: asyncio.create_task(save_tags(e))), ft.TextButton("Cancel", on_click=lambda _: setattr(page.dialog, 'open', False) or page.update())])
            page.dialog.open = True; page.update()

        async def settings_dialog(acc):
            phone_field = ft.TextField(label="Display Name", value=acc.get("phone", acc["session_name"]))
            notes_field = ft.TextField(label="Notes", value=acc.get("notes", ""), multiline=True)
            tags_field = ft.TextField(label="Tags", value=", ".join(acc.get("tags", [])))
            proxy_field = ft.TextField(label="Proxy", value=acc.get("proxy", ""))

            async def save_settings(e_save):
                page.dialog.open = False; page.update()
                all_accounts = load_accounts()
                for account in all_accounts:
                    if account['session_name'] == acc['session_name']:
                        account.update(phone=phone_field.value, notes=notes_field.value, tags=[t.strip() for t in tags_field.value.split(',') if t.strip()], proxy=proxy_field.value)
                        break
                save_accounts(all_accounts)
                await build_account_manager_content(container)

            page.dialog = ft.AlertDialog(modal=True, title=ft.Text("Settings"), content=ft.Column([phone_field, notes_field, tags_field, proxy_field]), actions=[ft.TextButton("Save", on_click=lambda e: asyncio.create_task(save_settings(e))), ft.TextButton("Cancel", on_click=lambda _: setattr(page.dialog, 'open', False) or page.update())])
            page.dialog.open = True; page.update()

        async def login_and_show_dialogs(acc):
            await build_dialogs_view(acc['session_name'])

        accounts = load_accounts()
        status_colors = {"unknown": "grey", "valid": "green", "invalid": "red"}
        account_list_view.controls = [
            ft.Container(
                data=acc,
                content=ft.Row(vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                    ft.Checkbox(width=20),
                    ft.Icon(name="circle", color=status_colors.get(acc.get('status', 'unknown')), size=12),
                    ft.VerticalDivider(width=5),
                    ft.Column([ft.Text(acc.get("phone", acc["session_name"]), weight=ft.FontWeight.BOLD), ft.Row([ft.Chip(ft.Text(tag, size=10)) for tag in acc.get("tags", [])], wrap=True)], spacing=2, expand=True),
                    ft.Row([
                        ft.ElevatedButton("Login", on_click=partial(lambda a: asyncio.create_task(login_and_show_dialogs(a)), acc)),
                        ft.IconButton(icon="settings", on_click=partial(lambda a: asyncio.create_task(settings_dialog(a)), acc)),
                        ft.IconButton(icon="delete_forever", icon_color="red", on_click=partial(lambda a: asyncio.create_task(delete_single_account(a)), acc))
                    ], spacing=5)
                ]),
                padding=10, border=ft.border.only(bottom=ft.BorderSide(1, "whitesmoke"))
            ) for acc in accounts
        ]
        
        container.content = ft.Column([
            ft.Row([ft.Text("Accounts", size=24), ft.ElevatedButton("Add Account", icon="add", on_click=lambda _: asyncio.create_task(build_login_view()))], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([ft.Checkbox(label="Select All"), ft.ElevatedButton("Delete Selected", on_click=lambda e: asyncio.create_task(delete_selected(e))), ft.ElevatedButton("Assign Tags", icon="label", on_click=lambda e: asyncio.create_task(assign_tags_dialog(e)))], spacing=10),
            ft.Divider(height=2),
            account_list_view,
        ], expand=True)
        await container.parent.update_async()

    # --- Login View --- #
    async def build_login_view():
        phone_field = ft.TextField(label="Phone Number", autofocus=True)
        code_field = ft.TextField(label="Code", visible=False)
        pw_field = ft.TextField(label="Password", password=True, visible=False)
        status = ft.Text()
        signin_button = ft.ElevatedButton("Get Code")
        
        client, phone_code_hash = None, None

        async def signin_flow(e):
            nonlocal client, phone_code_hash
            phone = phone_field.value.strip()
            session_name = phone.replace('+', '')
            signin_button.disabled = True; page.update()
            try:
                if not client:
                    client = TelegramClient(session_name, api_id, api_hash)
                    await client.connect()
                    result = await client.send_code_request(phone)
                    phone_code_hash = result.phone_code_hash
                    phone_field.disabled, code_field.visible, signin_button.text = True, True, "Sign In"
                    status.value = "Code sent."
                elif pw_field.visible:
                    await client.sign_in(password=pw_field.value.strip())
                else:
                    try:
                        await client.sign_in(phone, code_field.value.strip(), phone_code_hash=phone_code_hash)
                    except SessionPasswordNeededError:
                        pw_field.visible = True
                        signin_button.text = "Sign In with Password"
                        status.value = "2FA Password needed."
                        return
                
                # If we are here, login is successful
                accounts = load_accounts()
                if not any(a['session_name'] == session_name for a in accounts):
                    accounts.append({"session_name": session_name, "phone": phone, "status": "valid", "tags": [], "notes": "", "proxy": ""})
                    save_accounts(accounts)
                status.value = "Success! Returning..." 
                page.update(); await asyncio.sleep(1)
                await go_back_and_rebuild(e)

            except Exception as ex:
                status.value = f"Error: {ex}"
            finally:
                if status.value != "Success! Returning...":
                    signin_button.disabled = False
                page.update()

        view = ft.View("/add_account", [ft.AppBar(title=ft.Text("Add Account"), leading=ft.IconButton(icon=ft.icons.ARROW_BACK, on_click=go_back_and_rebuild)), ft.Column([phone_field, code_field, pw_field, signin_button, status])], padding=20)
        await go_to_view(view)

    # --- Dialogs View --- #
    async def build_dialogs_view(session_name):
        dialogs_list_view = ft.ListView(expand=True, spacing=5)
        status_text = ft.Text("Loading chats...")

        async def logout_and_back(e):
            await disconnect_client(session_name)
            await go_back_and_rebuild(e)

        view = ft.View(f"/{session_name}/dialogs", [ft.AppBar(title=ft.Text(f"Chats"), leading=ft.IconButton(icon=ft.icons.ARROW_BACK, on_click=logout_and_back)), ft.Column([status_text, dialogs_list_view])], padding=10)
        await go_to_view(view)
        
        client = await get_client(session_name)
        if client:
            status_text.visible = False
            async for dialog in client.iter_dialogs():
                dialogs_list_view.controls.append(ft.ListTile(title=ft.Text(dialog.name)))
            await page.update_async()
        else:
            status_text.value = "Could not connect to account."
            await page.update_async()

    # --- Initial App Shell --- #
    async def switch_main_content(e):
        idx = e.control.selected_index
        app_content_area.content = await (
            build_account_manager_content(app_content_area) if idx == 0 
            else build_ad_cabinet_content()
        )
        await app_content_area.update_async()

    rail = ft.NavigationRail(
        selected_index=0,
        on_change=lambda e: asyncio.create_task(switch_main_content(e)),
        destinations=[
            ft.NavigationRailDestination(icon="person_outline", label="Accounts"),
            ft.NavigationRailDestination(icon="campaign_outline", label="Ad Cabinet"),
        ]
    )

    initial_view = ft.View("/", [ft.Row([rail, ft.VerticalDivider(width=1), app_content_area], expand=True)])
    page.views.append(initial_view)
    await build_account_manager_content(app_content_area)

if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.WEB_BROWSER)
