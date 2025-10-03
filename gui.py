
import flet as ft
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
import asyncio

# Replace with your actual API ID and Hash
api_id = 26947469
api_hash = '731a222f9dd8b290db925a6a382159dd'

async def main(page: ft.Page):
    page.title = "Telegram Account Registration"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    # --- UI Elements ---
    session_name_field = ft.TextField(label="Session Name (e.g., account1)", width=300)
    phone_number_field = ft.TextField(label="Phone Number (+1234567890)", width=300)
    code_field = ft.TextField(label="Confirmation Code", width=300, visible=False)
    password_field = ft.TextField(label="2FA Password", password=True, width=300, visible=False)
    register_button = ft.ElevatedButton(text="Get Code", width=300)
    status_text = ft.Text()

    # --- Telethon Client Holder ---
    client_holder = {"client": None}

    # --- Event Handlers ---
    async def register_click(e):
        session_name = session_name_field.value.strip()
        phone_number = phone_number_field.value.strip()

        if not session_name or not phone_number:
            status_text.value = "Please fill in all fields."
            await page.update_async()
            return

        client = TelegramClient(session_name, api_id, api_hash)
        client_holder["client"] = client  # Store client
        await client.connect()

        if not await client.is_user_authorized():
            status_text.value = "Sending confirmation code..."
            await page.update_async()
            try:
                await client.send_code_request(phone_number)
                phone_number_field.visible = False
                code_field.visible = True
                register_button.text = "Sign In"
                status_text.value = "Code sent. Please check your Telegram app."
            except Exception as ex:
                status_text.value = f"Error: {ex}"
        else:
            status_text.value = "You are already signed in."
        
        await page.update_async()

    async def sign_in_click(e):
        client = client_holder.get("client")
        if not client:
            status_text.value = "Client not initialized. Please start over."
            await page.update_async()
            return

        phone_number = phone_number_field.value.strip()
        code = code_field.value.strip()
        password = password_field.value.strip()

        try:
            if password_field.visible:
                await client.sign_in(password=password)
            else:
                await client.sign_in(phone_number, code)
            
            me = await client.get_me()
            status_text.value = f"Welcome, {me.first_name}! Successfully signed in."
            # Hide all fields and button after successful login
            session_name_field.visible = False
            phone_number_field.visible = False
            code_field.visible = False
            password_field.visible = False
            register_button.visible = False

        except SessionPasswordNeededError:
            password_field.visible = True
            register_button.text = "Sign In with Password"
            status_text.value = "2FA enabled. Please enter your password."
        except Exception as ex:
            status_text.value = f"Sign-in error: {ex}"
        
        await page.update_async()

    async def button_logic_handler(e):
        if register_button.text == "Get Code":
            await register_click(e)
        else:
            await sign_in_click(e)

    register_button.on_click = button_logic_handler

    # --- Add controls to the page ---
    page.add(
        ft.Column(
            [
                ft.Text("Telegram Account Registration", size=24, weight=ft.FontWeight.BOLD),
                session_name_field,
                phone_number_field,
                code_field,
                password_field,
                register_button,
                status_text,
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20
        )
    )
    await page.update_async()

if __name__ == "__main__":
    ft.app(target=main)
