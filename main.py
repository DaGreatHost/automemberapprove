import asyncio, os, json
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

app = Client("chelpbot_full_clone", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

for file in ["posts.json", "channels.json", "scheduled.json"]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({}, f)

with open("posts.json", "r") as f:
    posts = json.load(f)
with open("channels.json", "r") as f:
    channels = json.load(f)
with open("scheduled.json", "r") as f:
    scheduled = json.load(f)

def get_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🖼️ Create Post", callback_data="create_post")],
        [InlineKeyboardButton("📋 My Posts", callback_data="my_posts")],
        [InlineKeyboardButton("📤 Schedule", callback_data="schedule_post"),
         InlineKeyboardButton("⚡ Send Now", callback_data="send_now")],
        [InlineKeyboardButton("➕ Add Channel", callback_data="add_channel"),
         InlineKeyboardButton("❌ Remove Channel", callback_data="remove_channel")],
        [InlineKeyboardButton("📂 Export", callback_data="export"),
         InlineKeyboardButton("📥 Import", callback_data="import_data")],
    ])

@app.on_message(filters.command("start"))
async def start(client, message: Message):
    await message.reply("Welcome to CHelpBot Clone!", reply_markup=get_main_menu())

@app.on_callback_query()
async def callback(client, cb: CallbackQuery):
    uid = str(cb.from_user.id)
    data = cb.data

    if data == "create_post":
        posts[uid] = {"step": "awaiting_content"}
        await cb.message.edit("Send your post text or photo with caption.")

    elif data == "my_posts":
        user_posts = posts.get(uid, {}).get("saved", [])
        if not user_posts:
            return await cb.message.edit("You have no saved posts.")
        text = "📋 Your Posts:
"
        for i, p in enumerate(user_posts, 1):
            text += f"{i}. {p['type']} post
"
        await cb.message.edit(text)

    elif data == "schedule_post":
        posts[uid] = {"step": "select_post"}
        await cb.message.edit("Send post number to schedule.")

    elif data == "send_now":
        posts[uid] = {"step": "send_now_select"}
        await cb.message.edit("Send post number to send now.")

    elif data == "add_channel":
        posts[uid] = {"step": "add_channel"}
        await cb.message.edit("Send Channel ID to add.")

    elif data == "remove_channel":
        user_chs = channels.get(uid, [])
        if not user_chs:
            return await cb.message.edit("No channels to remove.")
        txt = "Your Channels:
"
        for i, ch in enumerate(user_chs, 1):
            txt += f"{i}. {ch}
"
        posts[uid] = {"step": "remove_channel"}
        await cb.message.edit(txt + "
Send number to remove.")

    elif data == "export":
        if uid in posts:
            await cb.message.reply_document("posts.json")
        else:
            await cb.message.edit("No posts to export.")

    elif data == "import_data":
        await cb.message.edit("Send a .json file to import.")
        posts[uid] = {"step": "import"}

@app.on_message(filters.private & (filters.text | filters.photo))
async def collect_data(client, msg: Message):
    uid = str(msg.from_user.id)
    state = posts.get(uid, {}).get("step")

    if state == "awaiting_content":
        content = {
            "type": "photo" if msg.photo else "text",
            "text": msg.caption if msg.photo else msg.text
        }
        posts[uid]["temp"] = content
        posts[uid]["step"] = "awaiting_buttons"
        await msg.reply("Send buttons (text - url) per line or `skip`.")

    elif state == "awaiting_buttons":
        btn_text = msg.text.strip()
        content = posts[uid]["temp"]
        if btn_text.lower() != "skip":
            btns = []
            for line in btn_text.splitlines():
                if "-" in line:
                    t, u = line.split("-", 1)
                    btns.append([InlineKeyboardButton(t.strip(), u.strip())])
            content["buttons"] = [[b.text, b.url] for row in btns for b in row]
        posts[uid].setdefault("saved", []).append(content)
        posts[uid]["step"] = None
        with open("posts.json", "w") as f: json.dump(posts, f)
        await msg.reply("✅ Post saved!")

    elif state == "add_channel":
        cid = msg.text.strip()
        channels.setdefault(uid, []).append(cid)
        with open("channels.json", "w") as f: json.dump(channels, f)
        posts[uid]["step"] = None
        await msg.reply("✅ Channel added.")

    elif state == "remove_channel":
        try:
            idx = int(msg.text.strip()) - 1
            chs = channels[uid]
            chs.pop(idx)
            with open("channels.json", "w") as f: json.dump(channels, f)
            posts[uid]["step"] = None
            await msg.reply("✅ Channel removed.")
        except:
            await msg.reply("Invalid index.")

    elif state == "send_now_select":
        idx = int(msg.text.strip()) - 1
        content = posts[uid]["saved"][idx]
        markup = None
        if "buttons" in content:
            markup = InlineKeyboardMarkup([[InlineKeyboardButton(t, u)] for t, u in content["buttons"]])
        for cid in channels.get(uid, []):
            try:
                if content["type"] == "text":
                    await app.send_message(cid, content["text"], reply_markup=markup)
                else:
                    await app.send_photo(cid, photo=msg.photo.file_id, caption=content["text"], reply_markup=markup)
            except: pass
        await msg.reply("✅ Sent to all channels.")

@app.on_message(filters.document)
async def import_json(client, msg: Message):
    uid = str(msg.from_user.id)
    if posts.get(uid, {}).get("step") == "import":
        file = await msg.download()
        with open(file, "r") as f:
            new_data = json.load(f)
        posts[uid]["saved"] = new_data.get(uid, {}).get("saved", [])
        with open("posts.json", "w") as f: json.dump(posts, f)
        await msg.reply("✅ Imported successfully.")
        posts[uid]["step"] = None

app.run()
