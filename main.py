
import asyncio, json, os
from pyrogram import Client, filters
from pyrogram.types import ChatJoinRequest, Message

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CREATOR_ID = int(os.getenv("CREATOR_ID"))

app = Client("auto_accept_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Load delay config per channel
if os.path.exists("delay_config.json"):
    with open("delay_config.json", "r") as f:
        delay_config = json.load(f)
else:
    delay_config = {}

# Load welcome messages per channel
if os.path.exists("welcome_config.json"):
    with open("welcome_config.json", "r") as f:
        welcome_config = json.load(f)
else:
    welcome_config = {}

# Load approved user log
if os.path.exists("approved_users.json"):
    with open("approved_users.json", "r") as f:
        approved_users = json.load(f)
else:
    approved_users = []

@app.on_chat_join_request()
async def handle_join_request(client: Client, join: ChatJoinRequest):
    chat_id = str(join.chat.id)
    user_id = join.from_user.id

    delay_minutes = delay_config.get(chat_id, 0)
    if delay_minutes > 0:
        await asyncio.sleep(delay_minutes * 60)

    try:
        await join.approve()
        if user_id not in approved_users:
            approved_users.append(user_id)
            with open("approved_users.json", "w") as f:
                json.dump(approved_users, f)

        welcome = welcome_config.get(chat_id)
        if welcome:
            try:
                await client.send_message(user_id, welcome)
            except:
                pass
    except Exception as e:
        print(f"Failed to approve {user_id} in {chat_id}: {e}")

@app.on_message(filters.command("setwelcome"))
async def set_welcome(client, message: Message):
    if len(message.command) < 2:
        return await message.reply("Usage: /setwelcome <your message>")
    welcome_text = message.text.split(" ", 1)[1]
    welcome_config[str(message.chat.id)] = welcome_text
    with open("welcome_config.json", "w") as f:
        json.dump(welcome_config, f)
    await message.reply("✅ Welcome message set for this channel.")

@app.on_message(filters.command("totalusers"))
async def total_users(client, message: Message):
    if message.from_user.id != CREATOR_ID:
        return
    await message.reply(f"📊 Total approved users: {len(approved_users)}")

@app.on_message(filters.command("addchannel"))
async def add_channel(client, message: Message):
    try:
        parts = message.text.split()
        chat_id = parts[1]
        delay = int(parts[2])
        delay_config[chat_id] = delay
        with open("delay_config.json", "w") as f:
            json.dump(delay_config, f)
        await message.reply(f"✅ Channel `{chat_id}` added with {delay} min delay.", quote=True)
    except:
        await message.reply("Usage: /addchannel <channel_id> <delay_minutes>", quote=True)

@app.on_message(filters.command("viewchannels"))
async def view_channels(client, message: Message):
    if not delay_config:
        return await message.reply("❌ No channels configured yet.")
    reply = "📡 Tracked Channels:
"
    for ch, d in delay_config.items():
        reply += f"{ch} → {d} minute(s)
"
    await message.reply(reply)

@app.on_message(filters.command("help"))
async def help_cmd(client, message: Message):
    await message.reply("This bot auto-approves join requests.

Commands:
/setwelcome <msg> – Set DM welcome message
/viewchannels – View tracked channels
/help – Show this message")

app.run()
