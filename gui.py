
import flet as ft
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError, FloodWaitError
import asyncio
import os
import json

# --- Constants & Config --- #
api_id = 26947469
api_hash = '731a222f9dd8b290db925a6a382159dd'
ACCOUNTS_FILE = "accounts.json"

# --- Data Persistence --- #
def load_accounts():
    if not os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE, 'w') as f: json.dump([], f)
        return []
    with open(ACCOUNTS_FILE, 'r') as f:
        try: return json.load(f)
        except json.JSONDecodeError: return []

def save_accounts(accounts):
    with open(ACCOUNTS_FILE, 'w') as f:
        json.dump(accounts, f, indent=4)

# --- Main Application --- #
async def main(page: ft.Page):
    page.title = "Telegram Marketing Tool"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.STRETCH

    for folder in ["downloads/avatars", "downloads/media"]:
        if not os.path.exists(folder): os.makedirs(folder)

    client_holder = {"client": None}
    main_content_area = ft.Container(expand=True)

    async def show_account_manager_view():
        await show_account_manager(main_content_area)

    async def show_account_manager(content_area):
        status_text = ft.Text()

        async def login_and_show_dialogs(account):
            session_name = account['session_name']
            client = TelegramClient(session_name, api_id, api_hash)
            client_holder["client"] = client
            status_text.value = f"Connecting with {account.get('phone', session_name)}..."
            await page.update()
            try:
                await client.connect()
                if not await client.is_user_authorized():
                    status_text.value = f"Session for {session_name} is invalid."
                    await page.update()
                    return
                await show_dialogs_view(content_area, client)
            except Exception as e:
                status_text.value = f"Failed to connect: {e}"
                await page.update()

        async def login_button_clicked(e):
            await login_and_show_dialogs(e.control.data)

        def edit_account_clicked(e):
            account_to_edit = e.control.data
            notes_field = ft.TextField(label="Notes", value=account_to_edit.get("notes", ""), multiline=True)
            tags_field = ft.TextField(label="Tags (comma-separated)", value=", ".join(account_to_edit.get("tags", [])))

            async def save_data(e):
                all_accounts = load_accounts()
                for acc in all_accounts:
                    if acc['session_name'] == account_to_edit['session_name']:
                        acc['notes'] = notes_field.value
                        acc['tags'] = [tag.strip() for tag in tags_field.value.split(',') if tag.strip()]
                        break
                save_accounts(all_accounts)
                page.dialog.open = False
                await page.update()
                await show_account_manager_view()

            def close_dialog(e):
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
            await show_login_form(content_area)

        async def import_sessions_clicked(e):
            imported_count = 0
            existing_accounts = load_accounts()
            existing_session_names = {acc['session_name'] for acc in existing_accounts}
            for f in os.listdir('.'):
                if f.endswith('.session'):
                    session_name = f.replace('.session', '')
                    if session_name not in existing_session_names:
                        existing_accounts.append({
                            "session_name": session_name, "phone": session_name,
                            "status": "imported", "notes": "Imported session", "tags": []
                        })
                        imported_count += 1
            if imported_count > 0:
                save_accounts(existing_accounts)
                await show_account_manager_view()
            else:
                status_text.value = "No new session files found to import."
                await page.update()

        accounts = load_accounts()
        account_list_view = ft.ListView(expand=True, spacing=1, padding=0)
        for acc in accounts:
            tags_row = ft.Row(wrap=True, spacing=4, run_spacing=4)
            for tag in acc.get("tags", []):
                tags_row.controls.append(ft.Chip(ft.Text(tag, size=10), bgcolor=ft.colors.BLUE_100, padding=4))
            account_list_view.controls.append(ft.Container(
                content=ft.Row(vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                    ft.Icon("person_outline", size=24),
                    ft.VerticalDivider(),
                    ft.Column([
                        ft.Text(acc.get("phone", acc["session_name"]), weight=ft.FontWeight.BOLD),
                        ft.Text(acc.get("notes") or "No notes", italic=True, size=12, color=ft.colors.GREY),
                        tags_row
                    ], spacing=2, expand=True),
                    ft.Row([
                        ft.ElevatedButton("Login", on_click=login_button_clicked, data=acc),
                        ft.IconButton(icon="edit_note", on_click=edit_account_clicked, data=acc, tooltip="Edit notes and tags")
                    ], spacing=5)
                ]),
                padding=10, border=ft.border.only(bottom=ft.BorderSide(1, ft.colors.WHITE_SMOKE))
            ))

        content_area.content = ft.Column([
            ft.Row([
                ft.Text("Accounts", size=24, weight=ft.FontWeight.BOLD),
                ft.Row([
                    ft.ElevatedButton("Import Sessions", icon="download", on_click=import_sessions_clicked),
                    ft.ElevatedButton("Add Account", icon="add", on_click=add_account_clicked)
                ])
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Divider(height=2),
            account_list_view,
            status_text
        ], expand=True)
        await page.update()

    async def show_login_form(content_area):
        phone_field = ft.TextField(label="Phone Number (+1234567890)", width=300)
        code_field = ft.TextField(label="Confirmation Code", width=300, visible=False)
        pw_field = ft.TextField(label="2FA Password", password=True, width=300, visible=False)
        status = ft.Text()

        async def get_code_or_signin(e):
            phone = phone_field.value.strip()
            session_name = phone.replace('+', '')
            try:
                if not code_field.visible:
                    client = TelegramClient(session_name, api_id, api_hash)
                    client_holder["client"] = client
                    await client.connect()
                    await client.send_code_request(phone)
                    phone_field.disabled = True
                    code_field.visible = True
                    e.control.text = "Sign In"
                    status.value = "Code sent. Please check Telegram."
                else:
                    client = client_holder["client"]
                    if pw_field.visible:
                        await client.sign_in(password=pw_field.value.strip())
                    else:
                        await client.sign_in(phone, code_field.value.strip())
                    accounts = load_accounts()
                    if not any(a['session_name'] == session_name for a in accounts):
                        accounts.append({"session_name": session_name, "phone": phone, "notes": "", "tags": []})
                        save_accounts(accounts)
                    await show_account_manager_view()
            except SessionPasswordNeededError:
                pw_field.visible = True
                e.control.text = "Sign In with Password"
                status.value = "2FA Password needed."
            except Exception as ex:
                status.value = f"Error: {ex}"
            await page.update()

        signin_button = ft.ElevatedButton("Get Code", width=300, on_click=get_code_or_signin)

        content_area.content = ft.Column([
            ft.Row([ft.ElevatedButton("Back to Accounts", on_click=lambda e: show_account_manager_view())]),
            ft.Text("Add New Account", size=24),
            phone_field, code_field, pw_field, signin_button, status
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20)
        await page.update()

    async def show_dialogs_view(content_area, client):
        dialogs_list_view = ft.ListView(expand=True, spacing=10)
        status_text = ft.Text("Loading chats...")

        async def on_chat_click(e):
            await show_chat_messages_view(content_area, client, e.control.data['id'], e.control.data['name'])

        async def disconnect_and_go_back(e):
            if client and client.is_connected(): await client.disconnect()
            client_holder["client"] = None
            await show_account_manager_view()

        content_area.content = ft.Column([
            ft.Row([
                ft.Text("Your Chats", size=24, weight=ft.FontWeight.BOLD),
                ft.ElevatedButton("Logout", icon="logout", on_click=disconnect_and_go_back, bgcolor=ft.colors.RED_200)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            status_text,
            dialogs_list_view
        ], expand=True)
        await page.update()

        try:
            async for dialog in client.iter_dialogs():
                initials = "".join([p[0] for p in dialog.name.split()[:2]]).upper()
                trailing_widget = None
                if dialog.unread_count > 0:
                    trailing_widget = ft.CircleAvatar(content=ft.Text(str(dialog.unread_count)), bgcolor=ft.colors.BLUE_400, radius=12)
                list_tile = ft.ListTile(
                    leading=ft.CircleAvatar(content=ft.Text(initials)),
                    title=ft.Text(dialog.name, weight=ft.FontWeight.BOLD),
                    trailing=trailing_widget,
                    data={'id': dialog.id, 'name': dialog.name},
                    on_click=on_chat_click
                )
                dialogs_list_view.controls.append(list_tile)
            status_text.visible = False
        except Exception as e:
            status_text.value = f"Error loading chats: {e}"
        await page.update()

    async def show_chat_messages_view(content_area, client, chat_id, chat_name):
        messages_list_view = ft.ListView(expand=True, spacing=10, auto_scroll=True)
        await client.send_read_acknowledge(chat_id)

        async def go_back(e):
            await show_dialogs_view(content_area, client)

        message_input = ft.TextField(hint_text="Type a message...", expand=True)

        async def send_message_click(e):
            if message_input.value:
                await client.send_message(chat_id, message_input.value)
                messages_list_view.controls.append(ft.Text(f"You: {message_input.value}", text_align=ft.TextAlign.RIGHT))
                message_input.value = ""
                await page.update()

        content_area.content = ft.Column([
            ft.ElevatedButton("Back to Chats", on_click=go_back),
            messages_list_view,
            ft.Row([message_input, ft.IconButton(icon="send", on_click=send_message_click)])
        ], expand=True)
        await page.update()

        async for message in client.iter_messages(chat_id, limit=50):
            sender_name = "You" if message.out else (message.sender.first_name if message.sender else "Unknown")
            messages_list_view.controls.insert(0, ft.Text(f"{sender_name}: {message.text}"))
        await page.update()

    async def show_ad_cabinet_view(content_area):
        accounts = load_accounts()
        sender_checkboxes = [ft.Checkbox(label=acc.get('phone', acc['session_name']), data=acc) for acc in accounts]
        target_chats_field = ft.TextField(label="Target Chats (@username or invite link, one per line)", multiline=True, min_lines=3)
        message_box = ft.TextField(label="Your message", multiline=True, min_lines=5)
        delay_slider = ft.Slider(min=1, max=60, divisions=59, label="{value}s delay", value=5)
        status_log = ft.ListView(expand=True, spacing=5, auto_scroll=True)

        async def start_sending_click(e):
            senders = [cb.data for cb in sender_checkboxes if cb.value]
            targets = [line.strip() for line in target_chats_field.value.splitlines() if line.strip()]
            message = message_box.value
            delay = int(delay_slider.value)

            if not all([senders, targets, message]):
                status_log.controls.append(ft.Text("Error: Senders, targets, and message are required.", color=ft.colors.RED))
                await page.update()
                return

            e.control.disabled = True
            await page.update()

            for sender_acc in senders:
                status_log.controls.append(ft.Text(f"--- Logging in with {sender_acc.get('phone')} ---", weight=ft.FontWeight.BOLD))
                await page.update()
                client = TelegramClient(sender_acc['session_name'], api_id, api_hash)
                try:
                    await client.connect()
                    if not await client.is_user_authorized():
                        status_log.controls.append(ft.Text(f"    -> Auth failed, skipping.", color=ft.colors.RED))
                        continue

                    for target in targets:
                        try:
                            status_log.controls.append(ft.Text(f"    -> Sending to {target}..."))
                            await page.update()
                            await client.send_message(target, message)
                            status_log.controls.append(ft.Text(f"    -> Success! Waiting for {delay}s.", color=ft.colors.GREEN))
                            await page.update()
                            await asyncio.sleep(delay)
                        except FloodWaitError as fwe:
                            status_log.controls.append(ft.Text(f"    -> Flood wait! Sleeping for {fwe.seconds}s.", color=ft.colors.ORANGE))
                            await page.update()
                            await asyncio.sleep(fwe.seconds)
                        except Exception as ex:
                            status_log.controls.append(ft.Text(f"    -> Failed to send to {target}: {ex}", color=ft.colors.RED))
                            await page.update()
                finally:
                    if client.is_connected(): await client.disconnect()
                    status_log.controls.append(ft.Text(f"--- Session {sender_acc.get('phone')} finished ---\n"))
                    await page.update()

            status_log.controls.append(ft.Text("====== All tasks finished ======", weight=ft.FontWeight.BOLD))
            e.control.disabled = False
            await page.update()

        content_area.content = ft.Column([
            ft.Text("Ad Cabinet", size=24, weight=ft.FontWeight.BOLD),
            ft.Text("1. Select accounts to send from:"),
            ft.Container(content=ft.Column(sender_checkboxes), border=ft.border.all(1, ft.colors.BLACK26), padding=10, border_radius=5),
            ft.Text("2. Enter target chats (one per line):"),
            target_chats_field,
            ft.Text("3. Compose your message:"),
            message_box,
            ft.Text("4. Set delay between messages:"),
            delay_slider,
            ft.ElevatedButton("Start Sending", icon="rocket_launch", on_click=start_sending_click),
            ft.Divider(),
            ft.Text("Status Log:"),
            ft.Container(content=status_log, expand=True, border=ft.border.all(1, ft.colors.BLACK26), padding=10, border_radius=5)
        ], expand=True, scroll=ft.ScrollMode.ADAPTIVE)
        await page.update()

    async def nav_rail_changed(e):
        idx = e.control.selected_index
        if idx == 0: await show_account_manager_view()
        elif idx == 1: await show_ad_cabinet_view(main_content_area)

    rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=100,
        min_extended_width=200,
        group_alignment=-0.9,
        destinations=[
            ft.NavigationRailDestination(icon="person_outline", selected_icon="person", label="Accounts"),
            ft.NavigationRailDestination(icon="campaign_outline", selected_icon="campaign", label="Ad Cabinet"),
        ],
        on_change=nav_rail_changed,
    )

    page.add(ft.Row([rail, ft.VerticalDivider(width=1), main_content_area], expand=True))
    await show_account_manager_view()

if __name__ == "__main__":
    ft.app(target=main)
