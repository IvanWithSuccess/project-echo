
import asyncio
import json
import os
import random
import time
import logging
from project_echo.services.telegram_service import TelegramService

# --- Constants ---
CAMPAIGNS_FILE = "campaigns.json"
AUDIENCE_DIR = "audiences"
API_ID = 26947469
API_HASH = "731a222f9dd8b290db925a6a382159dd"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [WORKER] - %(message)s')

# --- Utility Functions ---
def load_json(file_path, default=None):
    try:
        with open(file_path, 'r') as f: return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default if default is not None else []

def save_json(file_path, data):
    with open(file_path, 'w') as f: json.dump(data, f, indent=2)

def find_and_update_campaign_status(campaign_id, new_status):
    campaigns = load_json(CAMPAIGNS_FILE)
    for campaign in campaigns:
        if campaign['id'] == campaign_id:
            campaign['status'] = new_status
            save_json(CAMPAIGNS_FILE, campaigns)
            logging.info(f"Updated campaign {campaign_id} to status: {new_status}")
            return True
    return False

async def process_campaign(campaign):
    campaign_id = campaign['id']
    audience_file = campaign['audience']
    message = campaign['message']
    sending_accounts = campaign['accounts']

    logging.info(f"Starting processing for campaign: {campaign['name']} ({campaign_id})")
    find_and_update_campaign_status(campaign_id, "In Progress")

    # Load audience
    audience_path = os.path.join(AUDIENCE_DIR, audience_file)
    users = load_json(audience_path)
    if not users:
        logging.error(f"Audience file {audience_file} is empty or not found. Aborting.")
        find_and_update_campaign_status(campaign_id, "Failed: Empty Audience")
        return

    logging.info(f"Loaded {len(users)} users from {audience_file}.")
    total_users = len(users)
    sent_count = 0
    failed_count = 0
    account_index = 0

    for i, user in enumerate(users):
        phone = sending_accounts[account_index]
        user_id = user.get('id')
        username = user.get('username', 'N/A')

        if not user_id:
            logging.warning(f"Skipping user with no ID: {user}")
            failed_count += 1
            continue

        service = TelegramService(phone, API_ID, API_HASH)
        logging.info(f"Attempting to send message to user #{i+1}/{total_users} ({username}) using account {phone}")
        
        status = await service.send_message(user_id, message)

        if status == "SUCCESS":
            sent_count += 1
            logging.info(f"Successfully sent to {username}.")
        else:
            failed_count += 1
            logging.warning(f"Failed to send to {username}. Reason: {status}")

        # Rotate to the next account for the next user
        account_index = (account_index + 1) % len(sending_accounts)

        # Sleep to mimic human behavior and avoid bans
        sleep_time = random.randint(10, 30) # 10-30 seconds
        if i < total_users - 1: # No need to sleep after the last message
             logging.info(f"Sleeping for {sleep_time} seconds...")
             await asyncio.sleep(sleep_time)

    final_status = f"Completed: {sent_count} sent, {failed_count} failed."
    find_and_update_campaign_status(campaign_id, final_status)
    logging.info(f"Finished campaign {campaign_id}. {final_status}")

async def main_loop():
    logging.info("Worker started. Looking for queued campaigns...")
    while True:
        campaigns = load_json(CAMPAIGNS_FILE)
        queued_campaign = next((c for c in campaigns if c.get('status') == 'Queued'), None)

        if queued_campaign:
            await process_campaign(queued_campaign)
        else:
            # If no campaigns, wait a bit before checking again
            time.sleep(10) 

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logging.info("Worker stopped by user.")

