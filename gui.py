
import flet as ft
from telethon import TelegramClient, events
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
        is_connected = False
        if client:
            try:
                is_connected = client.is_connected() and await client.is_user_authorized()
            except Exception: is_connected = False

        if not is_connected:
            logging.info(f"Creating new client for {session_name}")
            client = TelegramClient(session_name, api_id, api_hash)
            await client.connect()
            if not client.is_connected() or not await client.is_user_authorized():
                logging.warning(f"Authorization failed for {session_name}. Disconnecting.")
                await client.disconnect()
                return None
            active_clients[session_name] = client
        else:
            logging.info(f"Reusing existing client for {session_name}")
        return active_clients.get(session_name)

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
    for session_name in sessions:
        await disconnect_client(session_name)

# --- Data Persistence --- #
def load_accounts():
    if not os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE, 'w') as f: json.dump([], f)
        return []
    with open(ACCOUNTS_FILE, 'r') as f:
        try:
            accounts = json.load(f)
            for acc in accounts:
                if 'status' not in acc: acc['status'] = 'unknown'
            return accounts
        except json.JSONDecodeError: return []

def save_accounts(accounts):
    with open(ACCOUNTS_FILE, 'w') as f:
        json.dump(accounts, f, indent=4)

# --- Main Application --- #
async def main(page: ft.Page):
    logging.info("Application started.")
    page.title = "Telegram Marketing Tool"

    async def on_window_event(e):
        if e.data == "close":
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

    async def show_view(view_coroutine, *args):
        content = await view_coroutine(*args)
        main_content_area.content = content
        main_content_area.update()

    async def show_account_manager():
        status_text = ft.Text()

        async def login_and_show_dialogs(e):
            account = e.control.data
            phone_display = account.get('phone', account['session_name'])
            status_text.value = f"Connecting with {phone_display}..."
            status_text.update()
            client = await get_client(account['session_name'])
            if client:
                logging.info(f"Successfully got client for {phone_display}")
                await show_view(show_dialogs_view, client)
            else:
                msg = f"Failed to connect with {phone_display}."
                status_text.value = msg
                logging.error(msg)
                status_text.update()

        async def check_all_accounts_status(e):
            check_btn = e.control
            check_btn.disabled = True
            check_btn.update()
            accounts = load_accounts()
            for acc in accounts:
                phone_display = acc.get('phone', acc['session_name'])
                status_text.value = f"Checking {phone_display}..."
                status_text.update()
                client = await get_client(acc['session_name'])
                if client:
                    acc['status'] = 'valid'
                    await disconnect_client(acc['session_name'])
                else:
                    acc['status'] = 'invalid'
                save_accounts(accounts)
                await show_view(show_account_manager)
                await asyncio.sleep(0.5)
            status_text.value = "All accounts checked."
            check_btn.disabled = False
            status_text.update()

        async def edit_account_clicked(e):
            # This logic remains the same as it deals with UI and JSON, not clients
            pass # Placeholder for brevity, original logic is sound

        async def add_account_clicked(e):
            await show_view(show_login_form)

        async def import_sessions_clicked(e):
            # This logic also remains the same
            pass # Placeholder for brevity
        
        # ... (Rebuild the account list view as before) ...
        accounts = load_accounts()
        # ... (UI building logic) ...
        
        return ft.Column([ ... ]) # Return the content for show_view

    async def show_login_form():
        phone_field = ft.TextField(label="Phone Number (+1234567890)")
        code_field = ft.TextField(label="Confirmation Code", visible=False)
        pw_field = ft.TextField(label="2FA Password", password=True, visible=False)
        status = ft.Text()

        async def get_code_or_signin(e):
            phone = phone_field.value.strip()
            session_name = phone.replace('+', '')
            temp_client = TelegramClient(session_name, api_id, api_hash)

            try:
                if not code_field.visible:
                    await temp_client.connect()
                    await temp_client.send_code_request(phone)
                    # ... (update UI) ...
                else:
                    await temp_client.connect()
                    password = pw_field.value.strip()
                    if password:
                        await temp_client.sign_in(password=password)
                    else:
                        await temp_client.sign_in(phone, code_field.value.strip())
                    # ... (update accounts.json) ...
            except Exception as ex:
                # ... (handle errors) ...
            finally:
                if temp_client.is_connected():
                    await temp_client.disconnect()
                await show_view(show_account_manager)

        return ft.Column([ ... ]) # Return the content for show_view

    async def show_dialogs_view(client):
        async def disconnect_and_go_back(e):
            await disconnect_client(client.session.string)
            await show_view(show_account_manager)

        # ... (rest of the dialogs view logic) ...
        return ft.Column([ ... ]) # Return the content

    async def show_ad_cabinet_view():
        # ... (UI setup) ...
        status_log = ft.ListView(expand=True, spacing=5, auto_scroll=True)

        def local_log(message):
            status_log.controls.append(ft.Text(f"[{datetime.now().strftime('%H:%M:%S')}] {message}"))
            status_log.update()
            logging.info(message)

        async def start_sending_click(e):
            e.control.disabled = True
            e.control.update()

            senders = [cb.data for cb in sender_checkboxes if cb.value]
            targets = [line.strip() for line in target_chats_field.value.splitlines() if line.strip()]
            message = message_box.value
            delay = int(delay_slider.value)
            media_path = selected_file_path.value

            if not all([senders, targets]) or (not message and not media_path):
                local_log("Error: Senders, targets, and a message or media file are required.")
                e.control.disabled = False
                e.control.update()
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
            e.control.disabled = False
            e.control.update()

        return ft.Column([ ... ]) # Return the content

    async def nav_rail_changed(e):
        idx = e.control.selected_index
        if idx == 0: await show_view(show_account_manager)
        elif idx == 1: await show_view(show_ad_cabinet_view)

    # ... (Rail setup) ...
    page.add(ft.Row([rail, ft.VerticalDivider(width=1), main_content_area], expand=True))
    await show_view(show_account_manager)

if __name__ == "__main__":
    ft.app(target=main)
