import asyncio, os, json
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

app = Client("chelpbot_full_clone", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

for file in ["posts.json", "channels.json", "scheduled.json", "analytics.json"]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({}, f)

with open("posts.json", "r") as f: posts = json.load(f)
with open("channels.json", "r") as f: channels = json.load(f)
with open("scheduled.json", "r") as f: scheduled = json.load(f)
with open("analytics.json", "r") as f: analytics = json.load(f)

# Helper UI

def get_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🖼️ Create Post", callback_data="create_post")],
        [InlineKeyboardButton("📋 My Posts", callback_data="my_posts")],
        [InlineKeyboardButton("📤 Schedule", callback_data="schedule_post"),
         InlineKeyboardButton("⚡ Send Now", callback_data="send_now")],
        [InlineKeyboardButton("♻ Recurring", callback_data="recurring")],
        [InlineKeyboardButton("➕ Add Channel", callback_data="add_channel"),
         InlineKeyboardButton("❌ Remove Channel", callback_data="remove_channel")],
        [InlineKeyboardButton("📂 Export", callback_data="export"),
         InlineKeyboardButton("📥 Import", callback_data="import_data")],
        [InlineKeyboardButton("📊 Analytics", callback_data="analytics")],
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
        text = "📋 Your Posts:\n"
        for i, p in enumerate(user_posts, 1):
            text += f"{i}. {p['type']} post\n"
        posts[uid]["step"] = None
        await cb.message.edit(text)

    elif data == "schedule_post":
        posts[uid] = {"step": "schedule_select"}
        await cb.message.edit("Send post number to schedule. Format: post_number delay_minutes [auto_delete_minutes]")

    elif data == "send_now":
        posts[uid] = {"step": "send_now_select"}
        await cb.message.edit("Send post number to send now.")

    elif data == "recurring":
        posts[uid] = {"step": "recurring_setup"}
        await cb.message.edit("Send recurring format: post_number interval_minutes")

    elif data == "add_channel":
        posts[uid] = {"step": "add_channel"}
        await cb.message.edit("Send Channel ID to add.")

    elif data == "remove_channel":
        user_chs = channels.get(uid, [])
        if not user_chs:
            return await cb.message.edit("No channels to remove.")
        txt = "Your Channels:\n"
        for i, ch in enumerate(user_chs, 1):
            txt += f"{i}. {ch}\n"
        posts[uid] = {"step": "remove_channel"}
        await cb.message.edit(txt + "\nSend number to remove.")

    elif data == "export":
        if uid in posts:
            await cb.message.reply_document("posts.json")
        else:
            await cb.message.edit("No posts to export.")

    elif data == "import_data":
        await cb.message.edit("Send a .json file to import.")
        posts[uid] = {"step": "import"}

    elif data == "analytics":
        stats = analytics.get(uid, {"sent": 0, "scheduled": 0})
        await cb.message.edit(f"📊 Analytics\nSent: {stats['sent']}\nScheduled: {stats['scheduled']}")

@app.on_message(filters.private & (filters.text | filters.photo))
async def collect_data(client, msg: Message):
    uid = str(msg.from_user.id)
    state = posts.get(uid, {}).get("step")

    if state == "awaiting_content":
        content = {
            "type": "photo" if msg.photo else "text",
            "text": msg.caption if msg.photo else msg.text,
            "file_id": msg.photo.file_id if msg.photo else None
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
                    await app.send_photo(cid, photo=content["file_id"], caption=content["text"], reply_markup=markup)
            except: pass
        analytics.setdefault(uid, {"sent": 0, "scheduled": 0})["sent"] += 1
        with open("analytics.json", "w") as f: json.dump(analytics, f)
        await msg.reply("✅ Sent to all channels.")

    elif state == "schedule_select":
        try:
            args = msg.text.split()
            post_num = int(args[0]) - 1
            minutes = int(args[1])
            delete_after_min = int(args[2]) if len(args) > 2 else 0

            post = posts[uid]["saved"][post_num]
            sid = str(datetime.now().timestamp())
            scheduled.setdefault(uid, {})[sid] = {
                "time": (datetime.now() + timedelta(minutes=minutes)).timestamp(),
                "content": post,
                "auto_delete": delete_after_min
            }
            with open("scheduled.json", "w") as f: json.dump(scheduled, f)
            analytics.setdefault(uid, {"sent": 0, "scheduled": 0})["scheduled"] += 1
            with open("analytics.json", "w") as f: json.dump(analytics, f)
            posts[uid]["step"] = None
            await msg.reply(f"⏰ Scheduled in {minutes} min. Auto-delete: {delete_after_min} min")
        except:
            await msg.reply("❌ Invalid format. Usage: post_number delay_minutes [auto_delete_minutes]")

    elif state == "recurring_setup":
        try:
            args = msg.text.split()
            post_num = int(args[0]) - 1
            interval = int(args[1])
            post = posts[uid]["saved"][post_num]
            sid = f"recurring_{post_num}"
            scheduled.setdefault(uid, {})[sid] = {
                "time": (datetime.now() + timedelta(minutes=interval)).timestamp(),
                "content": post,
                "auto_delete": 0,
                "repeat_interval": interval
            }
            with open("scheduled.json", "w") as f: json.dump(scheduled, f)
            posts[uid]["step"] = None
            await msg.reply(f"♻️ Recurring post set every {interval} minutes.")
        except:
            await msg.reply("❌ Invalid format. Usage: post_number interval_minutes")

    elif state == "import":
        await msg.reply("Please upload a .json file.")

@app.on_message(filters.document)
async def import_json(client, msg: Message):
    uid = str(msg.from_user.id)
    if posts.get(uid, {}).get("step") == "import":
        file = await msg.download()
        with open(file, "r") as f:
            new_data = json.load(f)
        posts[uid]["saved"] = new_data.get(uid, {}).get("saved", [])
        with open("posts.json", "w") as f: json.dump(posts, f)
        posts[uid]["step"] = None
        await msg.reply("✅ Imported successfully.")

async def scheduler():
    while True:
        now = datetime.now().timestamp()
        for uid in scheduled:
            for sid, task in list(scheduled[uid].items()):
                if task["time"] <= now:
                    content = task["content"]
                    markup = None
                    if "buttons" in content:
                        markup = InlineKeyboardMarkup([[InlineKeyboardButton(t, u)] for t, u in content["buttons"]])
                    for cid in channels.get(uid, []):
                        try:
                            if content["type"] == "text":
                                msg = await app.send_message(cid, content["text"], reply_markup=markup)
                            else:
                                msg = await app.send_photo(cid, content["file_id"], caption=content["text"], reply_markup=markup)
                            if task.get("auto_delete"):
                                asyncio.create_task(delete_after(cid, msg.id, task["auto_delete"]))
                        except: pass
                    if "repeat_interval" in task:
                        task["time"] = (datetime.now() + timedelta(minutes=task["repeat_interval"])).timestamp()
                    else:
                        del scheduled[uid][sid]
                    with open("scheduled.json", "w") as f: json.dump(scheduled, f)
        await asyncio.sleep(20)

async def delete_after(chat_id, msg_id, delay):
    await asyncio.sleep(delay * 60)
    try:
        await app.delete_messages(chat_id, msg_id)
    except: pass

app.run(asyncio.gather(app.start(), scheduler()))
