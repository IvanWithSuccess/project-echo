
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

    # --- Directory Setup ---
    for folder in ["downloads/avatars", "downloads/media"]:
        if not os.path.exists(folder): os.makedirs(folder)

    client_holder = {"client": None}

    # --- UI Views --- #
    async def show_account_manager(content_area):
        content_area.clean()
        accounts = load_accounts()
        account_list_view = ft.ListView(expand=True, spacing=1, padding=0)
        status_text = ft.Text()

        async def login_and_show_dialogs(account):
            session_name = account['session_name']
            client = TelegramClient(session_name, api_id, api_hash)
            client_holder["client"] = client
            status_text.value = f"Connecting with {account.get('phone', session_name)}..."
            await status_text.update_async()
            try:
                await client.connect()
                if not await client.is_user_authorized():
                    status_text.value = f"Session for {session_name} is invalid."
                    await status_text.update_async()
                    return
                # Navigate to chats view for this client
                content_area.clean()
                await show_dialogs_view(content_area, client)

            except Exception as e:
                status_text.value = f"Failed to connect: {e}"
                await status_text.update_async()

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
                await page.update_async()
                await show_account_manager(content_area) # Refresh view
            
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

        account_list_view.controls.clear()
        for acc in accounts:
            tags_row = ft.Row(wrap=True, spacing=4, run_spacing=4)
            for tag in acc.get("tags", []):
                tags_row.controls.append(ft.Chip(ft.Text(tag, size=10), bgcolor="blue100", padding=4))

            account_list_view.controls.append(ft.Container(
                content=ft.Row(
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon("person_outline", size=24),
                        ft.VerticalDivider(),
                        ft.Column([
                            ft.Text(acc.get("phone", acc["session_name"]), weight=ft.FontWeight.BOLD),
                            ft.Text(acc.get("notes") or "No notes", italic=True, size=12, color="grey"),
                            tags_row
                        ], spacing=2, expand=True),
                        ft.Row([
                            ft.ElevatedButton("Login", on_click=login_button_clicked, data=acc),
                            ft.IconButton(icon="edit_note", on_click=edit_account_clicked, data=acc, tooltip="Edit notes and tags")
                        ], spacing=5)
                    ]),
                padding=10, border=ft.border.only(bottom=ft.BorderSide(1, "whitesmoke"))))

        async def import_sessions_clicked(e):
            # ... (import logic is the same)
            await show_account_manager(content_area)

        async def add_account_clicked(e):
            content_area.clean()
            await show_login_form(content_area)
        
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
        await content_area.update_async()

    async def show_ad_cabinet_view(content_area):
        content_area.clean()
        accounts = load_accounts()
        
        sender_checkboxes = [ft.Checkbox(label=acc.get('phone', acc['session_name']), data=acc) for acc in accounts]
        target_chats_field = ft.TextField(label="Target Chats (@username or invite link, one per line)", multiline=True, min_lines=5)
        message_box = ft.TextField(label="Your message", multiline=True, min_lines=5)
        delay_slider = ft.Slider(min=1, max=60, divisions=59, label="{value}s delay", value=5)
        status_log = ft.ListView(expand=True, spacing=5, auto_scroll=True)

        async def start_sending_click(e):
            senders = [cb.data for cb in sender_checkboxes if cb.value]
            targets = [line.strip() for line in target_chats_field.value.splitlines() if line.strip()]
            message = message_box.value
            delay = delay_slider.value

            if not senders or not targets or not message:
                status_log.controls.append(ft.Text("Error: Senders, targets, and message cannot be empty.", color="red"))
                await status_log.update_async(); return

            e.control.disabled = True
            await page.update_async()

            for sender_acc in senders:
                status_log.controls.append(ft.Text(f"-- Logging in with {sender_acc.get('phone')} --", weight="bold"))
                await status_log.update_async()
                client = TelegramClient(sender_acc['session_name'], api_id, api_hash)
                try:
                    await client.connect()
                    if not await client.is_user_authorized():
                        status_log.controls.append(ft.Text(f"    -> Auth failed, skipping.", color="red"))
                        continue

                    for target in targets:
                        try:
                            status_log.controls.append(ft.Text(f"    -> Sending to {target}..."))
                            await status_log.update_async()
                            await client.send_message(target, message)
                            status_log.controls.append(ft.Text(f"    -> Success! Waiting for {delay}s...", color="green"))
                            await status_log.update_async()
                            await asyncio.sleep(delay)
                        except FloodWaitError as fwe:
                            status_log.controls.append(ft.Text(f"    -> Flood wait! Sleeping for {fwe.seconds}s...", color="orange"))
                            await status_log.update_async()
                            await asyncio.sleep(fwe.seconds)
                        except Exception as ex:
                            status_log.controls.append(ft.Text(f"    -> Failed to send to {target}: {ex}", color="red"))
                            await status_log.update_async() 
                finally:
                    if client.is_connected(): await client.disconnect()
                    status_log.controls.append(ft.Text(f"-- Session {sender_acc.get('phone')} finished --\n"))
                    await status_log.update_async()
            
            status_log.controls.append(ft.Text("====== All tasks finished ======", weight="bold"))
            e.control.disabled = False
            await page.update_async()

        content_area.content = ft.Column([
                ft.Text("Ad Cabinet", size=24, weight=ft.FontWeight.BOLD),
                ft.Text("1. Select accounts to send from:"),
                ft.Container(content=ft.Column(sender_checkboxes), border=ft.border.all(1, "grey"), padding=10, border_radius=5),
                ft.Text("2. Enter target chats (one per line):"),
                target_chats_field,
                ft.Text("3. Compose your message:"),
                message_box,
                ft.Text("4. Set delay between messages:"),
                delay_slider,
                ft.ElevatedButton("Start Sending", icon="rocket_launch", on_click=start_sending_click, width=200),
                ft.Divider(),
                ft.Text("Status Log:"),
                ft.Container(content=status_log, expand=True, border=ft.border.all(1, "grey"), padding=10, border_radius=5)
        ], expand=True, scroll=ft.ScrollMode.ADAPTIVE)
        await content_area.update_async()
    
    # --- Placeholder for other views like show_dialogs_view, show_chat_messages, show_login_form --- #
    async def show_dialogs_view(content_area, client):
        # This view is now reached *after* logging in from the account manager
        pass # Simplified for this refactoring example
    
    async def show_login_form(content_area):
        pass # Simplified for this refactoring example

    # --- Main Layout & Navigation --- #
    main_content_area = ft.Container(expand=True)

    async def nav_rail_changed(e):
        selected_index = e.control.selected_index
        if selected_index == 0:
            await show_account_manager(main_content_area)
        elif selected_index == 1:
            await show_ad_cabinet_view(main_content_area)

    rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=100,
        min_extended_width=400,
        leading=ft.FloatingActionButton(icon="add", text="Account"), # Example action
        group_alignment=-0.9,
        destinations=[
            ft.NavigationRailDestination(icon="person_outline", selected_icon="person", label="Accounts"),
            ft.NavigationRailDestination(icon="campaign_outline", selected_icon="campaign", label="Ad Cabinet"),
        ],
        on_change=nav_rail_changed,
    )

    page.add(
        ft.Row(
            [rail, ft.VerticalDivider(width=1), main_content_area],
            expand=True,
        )
    )

    # Load initial view
    await show_account_manager(main_content_area)
    await page.update_async()


if __name__ == "__main__":
    ft.app(target=main)
