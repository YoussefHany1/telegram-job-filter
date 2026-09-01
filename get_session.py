import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from config import settings

async def main():
    # Use the existing SQLite session
    client = TelegramClient(settings.session_name, settings.api_id, settings.api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        print("You are not logged in. Please run app.py locally first to login.")
        return
    
    string_session = StringSession.save(client.session)
    print("\n" + "="*50)
    print("YOUR STRING SESSION:")
    print(string_session)
    print("="*50 + "\n")
    print("Copy the long string above and add it to your Render Environment Variables as STRING_SESSION.")

if __name__ == "__main__":
    asyncio.run(main())
