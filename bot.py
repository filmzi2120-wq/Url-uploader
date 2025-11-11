import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from pyrogram.enums import ParseMode
from config import Config
from database import db
from downloader import downloader
from helpers import Progress, humanbytes, is_url, is_magnet
import time
import random

# Initialize bot
app = Client(
    "url_uploader_bot",
    api_id=Config.APP_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

# User settings and tasks storage
user_settings = {}
user_tasks = {}
user_cooldowns = {}

# Cooldown settings
COOLDOWN_TIME = 159  # 2 minutes 39 seconds

# Random emojis for reactions
REACTION_EMOJIS = ["👍", "❤", "🔥", "🎉", "😍", "👏", "⚡", "✨", "💯", "🚀"]

def format_time(seconds):
    """Format seconds to minutes and seconds"""
    minutes = seconds // 60
    secs = seconds % 60
    if minutes > 0:
        return f"{minutes} minute{'s' if minutes > 1 else ''}, {secs} second{'s' if secs != 1 else ''}"
    return f"{secs} second{'s' if secs != 1 else ''}"

def get_remaining_time(user_id):
    """Get remaining cooldown time for user"""
    if user_id not in user_cooldowns:
        return 0
    
    elapsed = time.time() - user_cooldowns[user_id]
    remaining = COOLDOWN_TIME - elapsed
    
    if remaining <= 0:
        del user_cooldowns[user_id]
        return 0
    
    return int(remaining)

# Start command - Auto-filter style with random reaction
@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    await db.add_user(user_id, username, first_name)
    
    # Add random reaction to /start message
    try:
        random_emoji = random.choice(REACTION_EMOJIS)
        await message.react(random_emoji)
    except Exception as e:
        print(f"Reaction failed: {e}")
    
    text = Config.START_MESSAGE.format(
        name=first_name,
        dev=Config.DEVELOPER,
        channel=Config.UPDATE_CHANNEL
    )
    
    # Auto-filter style buttons
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📚 Help", callback_data="help"),
         InlineKeyboardButton("ℹ️ About", callback_data="about")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
         InlineKeyboardButton("📊 Status", callback_data="status")],
        [InlineKeyboardButton("📢 Updates Channel", url=Config.UPDATE_CHANNEL)]
    ])
    
    await message.reply_text(text, reply_markup=keyboard, disable_web_page_preview=True)

# Help command - Shows everything in one message
@app.on_callback_query(filters.regex("^help$"))
async def help_callback(client, callback: CallbackQuery):
    text = Config.HELP_MESSAGE.format(
        dev=Config.DEVELOPER,
        channel=Config.UPDATE_CHANNEL
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="back_start")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, disable_web_page_preview=True)

@app.on_message(filters.command("help") & filters.private)
async def help_command(client, message: Message):
    text = Config.HELP_MESSAGE.format(
        dev=Config.DEVELOPER,
        channel=Config.UPDATE_CHANNEL
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Start", callback_data="back_start")]
    ])
    
    await message.reply_text(text, reply_markup=keyboard, disable_web_page_preview=True)

# About command
@app.on_callback_query(filters.regex("^about$"))
async def about_callback(client, callback: CallbackQuery):
    text = Config.ABOUT_MESSAGE.format(
        dev=Config.DEVELOPER,
        channel=Config.UPDATE_CHANNEL
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✴️ Sources", url="https://github.com/zerodev6/URL-UPLOADER")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_start")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, disable_web_page_preview=True)

@app.on_message(filters.command("about") & filters.private)
async def about_command(client, message: Message):
    text = Config.ABOUT_MESSAGE.format(
        dev=Config.DEVELOPER,
        channel=Config.UPDATE_CHANNEL
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✴️ Sources", url="https://github.com/zerodev6/URL-UPLOADER")],
        [InlineKeyboardButton("🔙 Back to Start", callback_data="back_start")]
    ])
    
    await message.reply_text(text, reply_markup=keyboard, disable_web_page_preview=True)

# Settings menu
@app.on_callback_query(filters.regex("^settings$"))
async def settings_callback(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    settings = user_settings.get(user_id, {})
    
    text = """⚙️ **Bot Settings**

**Current Settings:**
• Custom filename: {}
• Custom caption: {}
• Thumbnail: {}

**How to set:**
📝 Send `/setname <filename>` - Set custom filename
💬 Send `/setcaption <text>` - Set custom caption
🖼️ Send a photo - Set as thumbnail
🗑️ Send `/clearsettings` - Clear all settings
👁️ Send `/showthumb` - View your thumbnail""".format(
        settings.get('filename', 'Not set'),
        'Set ✅' if settings.get('caption') else 'Not set',
        'Set ✅' if settings.get('thumbnail') else 'Not set'
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="back_start")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)

@app.on_message(filters.command("settings") & filters.private)
async def settings_command(client, message: Message):
    user_id = message.from_user.id
    settings = user_settings.get(user_id, {})
    
    text = """⚙️ **Bot Settings**

**Current Settings:**
• Custom filename: {}
• Custom caption: {}
• Thumbnail: {}

**How to set:**
📝 Send `/setname <filename>` - Set custom filename
💬 Send `/setcaption <text>` - Set custom caption
🖼️ Send a photo - Set as thumbnail
🗑️ Send `/clearsettings` - Clear all settings
👁️ Send `/showthumb` - View your thumbnail""".format(
        settings.get('filename', 'Not set'),
        'Set ✅' if settings.get('caption') else 'Not set',
        'Set ✅' if settings.get('thumbnail') else 'Not set'
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Start", callback_data="back_start")]
    ])
    
    await message.reply_text(text, reply_markup=keyboard)

# Status command
@app.on_callback_query(filters.regex("^status$"))
async def status_callback(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    user_data = await db.get_user(user_id)
    
    if user_data:
        text = f"""📊 **Your Statistics**

👤 **User Info:**
• ID: `{user_id}`
• Username: @{user_data.get('username', 'N/A')}
• Name: {user_data.get('first_name', 'N/A')}

📈 **Usage Stats:**
• Total Downloads: {user_data.get('total_downloads', 0)}
• Total Uploads: {user_data.get('total_uploads', 0)}
• Member since: {user_data.get('joined_date').strftime('%Y-%m-%d')}

⚡ **Bot Info:**
• Speed: 500 MB/s
• Max size: 4 GB
• Status: ✅ Online"""
    else:
        text = "No data found. Start using the bot!"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="back_start")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)

@app.on_message(filters.command("status") & filters.private)
async def status_command(client, message: Message):
    user_id = message.from_user.id
    user_data = await db.get_user(user_id)
    
    if user_data:
        text = f"""📊 **Your Statistics**

👤 **User Info:**
• ID: `{user_id}`
• Username: @{user_data.get('username', 'N/A')}
• Name: {user_data.get('first_name', 'N/A')}

📈 **Usage Stats:**
• Total Downloads: {user_data.get('total_downloads', 0)}
• Total Uploads: {user_data.get('total_uploads', 0)}
• Member since: {user_data.get('joined_date').strftime('%Y-%m-%d')}

⚡ **Bot Info:**
• Speed: 500 MB/s
• Max size: 4 GB
• Status: ✅ Online"""
    else:
        text = "No data found!"
    
    await message.reply_text(text)

# Back to start
@app.on_callback_query(filters.regex("^back_start$"))
async def back_start(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    first_name = callback.from_user.first_name
    
    text = Config.START_MESSAGE.format(
        name=first_name,
        dev=Config.DEVELOPER,
        channel=Config.UPDATE_CHANNEL
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📚 Help", callback_data="help"),
         InlineKeyboardButton("ℹ️ About", callback_data="about")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
         InlineKeyboardButton("📊 Status", callback_data="status")],
        [InlineKeyboardButton("📢 Updates Channel", url=Config.UPDATE_CHANNEL)]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, disable_web_page_preview=True)

# Handle file upload type selection
@app.on_callback_query(filters.regex("^upload_"))
async def handle_upload_type(client, callback: CallbackQuery):
    data = callback.data
    user_id = callback.from_user.id
    
    if user_id not in user_tasks:
        await callback.answer("⚠️ Task expired! Send URL again.", show_alert=True)
        return
    
    task = user_tasks[user_id]
    filepath = task['filepath']
    upload_type = data.split('_')[1]  # doc or video
    
    await callback.message.edit_text("⬆️ **Uploading to Telegram...**\n\nPlease wait...")
    
    try:
        # Get user settings
        settings = user_settings.get(user_id, {})
        thumbnail = settings.get('thumbnail')
        
        filename = os.path.basename(filepath)
        filesize = os.path.getsize(filepath) if os.path.isfile(filepath) else 0
        
        caption = settings.get('caption', 
            f"📁 **{filename}**\n\n"
            f"💾 **Size:** {humanbytes(filesize)}\n"
            f"⚡ **Speed:** 500 MB/s\n\n"
            f"**Uploaded by:** {Config.DEVELOPER}"
        )
        
        # Progress tracker
        progress = Progress(client, callback.message)
        
        if upload_type == 'doc':
            await client.send_document(
                chat_id=callback.message.chat.id,
                document=filepath,
                caption=caption,
                thumb=thumbnail,
                progress=progress.progress_callback,
                progress_args=("Uploading",)
            )
        else:
            # Get video metadata
            duration = width = height = 0
            try:
                import subprocess
                result = subprocess.run(
                    ['ffprobe', '-v', 'error', '-show_entries',
                     'format=duration:stream=width,height', '-of',
                     'default=noprint_wrappers=1', filepath],
                    capture_output=True, text=True, timeout=10
                )
                for line in result.stdout.split('\n'):
                    if 'duration=' in line:
                        duration = int(float(line.split('=')[1]))
                    elif 'width=' in line:
                        width = int(line.split('=')[1])
                    elif 'height=' in line:
                        height = int(line.split('=')[1])
            except:
                pass
            
            await client.send_video(
                chat_id=callback.message.chat.id,
                video=filepath,
                caption=caption,
                thumb=thumbnail,
                duration=duration,
                width=width,
                height=height,
                supports_streaming=True,
                progress=progress.progress_callback,
                progress_args=("Uploading",)
            )
        
        await db.update_stats(user_id, upload=True)
        await db.log_action(user_id, "upload", filepath)
        
        await callback.message.delete()
        
        # Set cooldown after successful upload
        user_cooldowns[user_id] = time.time()
        
        # Success message with cooldown
        remaining = get_remaining_time(user_id)
        time_str = format_time(remaining)
        
        await client.send_message(
            callback.message.chat.id,
            f"✅ **Upload Complete!**\n\n"
            f"You can send new task after {time_str}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Start", callback_data="back_start")]
            ])
        )
        
        # Start cooldown notification task
        asyncio.create_task(cooldown_notification(client, callback.message.chat.id, user_id))
        
        # Log to channel
        try:
            await client.send_message(
                Config.LOG_CHANNEL,
                f"📤 **New Upload**\n\n"
                f"👤 User: {callback.from_user.mention}\n"
                f"📁 File: `{filename}`\n"
                f"💾 Size: {humanbytes(filesize)}\n"
                f"📊 Type: {'Document' if upload_type == 'doc' else 'Video'}"
            )
        except:
            pass
        
    except Exception as e:
        await callback.message.edit_text(f"❌ **Upload Failed!**\n\n**Error:** {str(e)}")
    
    finally:
        downloader.cleanup(filepath)
        if user_id in user_tasks:
            del user_tasks[user_id]

async def cooldown_notification(client, chat_id, user_id):
    """Send notification when cooldown expires"""
    remaining = get_remaining_time(user_id)
    if remaining > 0:
        await asyncio.sleep(remaining)
    
    # Check if cooldown is still active (user might have been removed)
    if user_id in user_cooldowns:
        del user_cooldowns[user_id]
        
        try:
            await client.send_message(
                chat_id,
                "You can send new task now 🚀"
            )
        except:
            pass

# Handle rename callback
@app.on_callback_query(filters.regex("^rename_"))
async def handle_rename_callback(client, callback: CallbackQuery):
    data = callback.data
    user_id = callback.from_user.id
    
    if user_id not in user_tasks:
        await callback.answer("⚠️ Task expired!", show_alert=True)
        return
    
    if data == "rename_now":
        filename = os.path.basename(user_tasks[user_id]['filepath'])
        
        # Set waiting for rename
        user_tasks[user_id]['waiting_rename'] = True
        
        await callback.message.edit_text(
            f"📝 **Send new name for this file**\n\n"
            f"Current: `{filename}`\n\n"
            f"Type the new filename and send:"
        )
        await callback.answer("Type new filename and send")
        
    elif data == "rename_skip":
        # Skip rename, show upload options
        user_tasks[user_id]['waiting_rename'] = False
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📁 Upload as Document", callback_data="upload_doc")],
            [InlineKeyboardButton("🎥 Upload as Video", callback_data="upload_video")]
        ])
        
        await callback.message.edit_text(
            "**Choose upload type:**\n\nHow do you want to upload this file?",
            reply_markup=keyboard
        )
        await callback.answer()

# Handle rename input first
@app.on_message(filters.text & filters.private & ~filters.command(["start", "help", "about", "status", "settings", "setname", "setcaption", "clearsettings", "showthumb", "total", "broadcast"]))
async def handle_text_input(client, message: Message):
    user_id = message.from_user.id
    
    # Debug: Check if user has active task
    print(f"[DEBUG] User {user_id} sent text: {message.text[:50]}")
    print(f"[DEBUG] Active tasks: {user_id in user_tasks}")
    if user_id in user_tasks:
        print(f"[DEBUG] Waiting for rename: {user_tasks[user_id].get('waiting_rename', False)}")
    
    # Check if waiting for rename
    if user_id in user_tasks and user_tasks[user_id].get('waiting_rename'):
        new_name = message.text.strip()
        filepath = user_tasks[user_id]['filepath']
        
        print(f"[DEBUG] Renaming {filepath} to {new_name}")
        
        # Create new path with new name
        new_path = os.path.join(os.path.dirname(filepath), new_name)
        
        try:
            # Rename file
            if os.path.exists(filepath):
                os.rename(filepath, new_path)
                user_tasks[user_id]['filepath'] = new_path
                user_tasks[user_id]['waiting_rename'] = False
                
                print(f"[DEBUG] Rename successful!")
                
                # Show upload options
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📁 Upload as Document", callback_data="upload_doc")],
                    [InlineKeyboardButton("🎥 Upload as Video", callback_data="upload_video")]
                ])
                
                await message.reply_text(
                    f"✅ **Renamed to:** `{new_name}`\n\n**Choose upload type:**",
                    reply_markup=keyboard
                )
            else:
                print(f"[DEBUG] File not found: {filepath}")
                await message.reply_text("❌ **Error:** File not found!")
        except Exception as e:
            print(f"[DEBUG] Rename error: {str(e)}")
            await message.reply_text(f"❌ **Rename failed:** {str(e)}")
        return
    
    # If not waiting for rename, check if it's a URL
    url = message.text.strip()
    if not (is_url(url) or is_magnet(url)):
        print(f"[DEBUG] Not a valid URL, ignoring")
        return
    
    # Check cooldown before processing
    remaining = get_remaining_time(user_id)
    if remaining > 0:
        time_str = format_time(remaining)
        await message.reply_text(
            f"👆 See this message and wait till this time.\n\n"
            f"⏳ You can send new task after {time_str}"
        )
        return
    
    print(f"[DEBUG] Processing as download URL")
    # Process as download
    await process_download(client, message, url)

# Main download handler
@app.on_message(filters.document & filters.private)
async def handle_document(client, message: Message):
    user_id = message.from_user.id
    
    # Check cooldown for torrent uploads too
    remaining = get_remaining_time(user_id)
    if remaining > 0:
        time_str = format_time(remaining)
        await message.reply_text(
            f"👆 See this message and wait till this time.\n\n"
            f"⏳ You can send new task after {time_str}"
        )
        return
    
    # Check if it's a torrent file
    if message.document and message.document.file_name.endswith('.torrent'):
        torrent_path = await message.download()
        await process_download(client, message, torrent_path)

# Download processing function
async def process_download(client, message: Message, url):
    user_id = message.from_user.id
    
    await db.add_user(user_id, message.from_user.username, message.from_user.first_name)
    
    # Start download
    status_msg = await message.reply_text("🔄 **Processing your request...**\n\nStarting download...")
    
    try:
        # Download with progress
        progress = Progress(client, status_msg)
        filepath, error = await downloader.download(url, progress_callback=progress.progress_callback)
        
        if error:
            await status_msg.edit_text(f"❌ **Error:** {error}\n\nPlease check the URL and try again.")
            return
        
        await db.update_stats(user_id, download=True)
        await db.log_action(user_id, "download", str(url) if isinstance(url, str) else "torrent")
        
        # Store task
        user_tasks[user_id] = {
            'filepath': filepath,
            'url': url if isinstance(url, str) else 'torrent',
            'waiting_rename': False
        }
        
        # Get file info
        filename = os.path.basename(filepath)
        filesize = os.path.getsize(filepath) if os.path.isfile(filepath) else 0
        
        # Ask for rename
        text = (
            f"✅ **Download Complete!**\n\n"
            f"📁 **File:** `{filename}`\n"
            f"💾 **Size:** {humanbytes(filesize)}\n"
            f"⚡ **Speed:** 500 MB/s\n\n"
            f"📝 **Send new name for this file** - 📁 `{filename}`"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ Rename Now", callback_data="rename_now")],
            [InlineKeyboardButton("⏭️ Skip Rename", callback_data="rename_skip")]
        ])
        
        await status_msg.edit_text(text, reply_markup=keyboard)
        
        # Log to channel
        try:
            await client.send_message(
                Config.LOG_CHANNEL,
                f"📥 **New Download**\n\n"
                f"👤 User: {message.from_user.mention}\n"
                f"📁 File: `{filename}`\n"
                f"💾 Size: {humanbytes(filesize)}\n"
                f"🔗 Source: `{url if isinstance(url, str) else 'Torrent'}`"
            )
        except:
            pass
            
    except Exception as e:
        await status_msg.edit_text(f"❌ **Error:** {str(e)}\n\nSomething went wrong. Please try again.")
        await db.log_action(user_id, "error", str(e))

# Settings commands
@app.on_message(filters.command("setname") & filters.private)
async def setname_command(client, message: Message):
    user_id = message.from_user.id
    if len(message.command) < 2:
        await message.reply_text("**Usage:** `/setname filename.ext`\n\nExample: `/setname movie.mp4`")
        return
    
    filename = " ".join(message.command[1:])
    if user_id not in user_settings:
        user_settings[user_id] = {}
    user_settings[user_id]['filename'] = filename
    
    await message.reply_text(f"✅ **Filename set to:** `{filename}`")

@app.on_message(filters.command("setcaption") & filters.private)
async def setcaption_command(client, message: Message):
    user_id = message.from_user.id
    if len(message.command) < 2:
        await message.reply_text("**Usage:** `/setcaption Your caption here`")
        return
    
    caption = message.text.split(None, 1)[1]
    if user_id not in user_settings:
        user_settings[user_id] = {}
    user_settings[user_id]['caption'] = caption
    
    await message.reply_text("✅ **Caption set successfully!**")

@app.on_message(filters.command("clearsettings") & filters.private)
async def clearsettings_command(client, message: Message):
    user_id = message.from_user.id
    if user_id in user_settings:
        user_settings[user_id] = {}
    await message.reply_text("✅ **All settings cleared!**")

# Thumbnail handler
@app.on_message(filters.photo & filters.private)
async def handle_thumbnail(client, message: Message):
    user_id = message.from_user.id
    thumb_path = await message.download(file_name=f"{Config.DOWNLOAD_DIR}/thumb_{user_id}.jpg")
    
    if user_id not in user_settings:
        user_settings[user_id] = {}
    user_settings[user_id]['thumbnail'] = thumb_path
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑️ Delete Thumbnail", callback_data="delete_thumb")]
    ])
    
    await message.reply_text(
        "✅ **Saved your thumbnail**",
        reply_markup=keyboard
    )

# Show thumbnail command
@app.on_message(filters.command("showthumb") & filters.private)
async def showthumb_command(client, message: Message):
    user_id = message.from_user.id
    settings = user_settings.get(user_id, {})
    
    thumbnail = settings.get('thumbnail')
    
    if thumbnail and os.path.exists(thumbnail):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑️ Delete Thumbnail", callback_data="delete_thumb")]
        ])
        
        await message.reply_photo(
            photo=thumbnail,
            caption="📸 **Your Current Thumbnail**",
            reply_markup=keyboard
        )
    else:
        await message.reply_text(
            "❌ **No thumbnail set!**\n\n"
            "Send a photo to set as thumbnail."
        )

# Delete thumbnail callback
@app.on_callback_query(filters.regex("^delete_thumb$"))
async def delete_thumb_callback(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    settings = user_settings.get(user_id, {})
    
    thumbnail = settings.get('thumbnail')
    
    if thumbnail and os.path.exists(thumbnail):
        try:
            os.remove(thumbnail)
            user_settings[user_id]['thumbnail'] = None
            await callback.message.edit_caption(
                caption="✅ **Thumbnail deleted successfully!**"
            )
            await callback.answer("Thumbnail deleted!", show_alert=True)
        except Exception as e:
            await callback.answer(f"Error: {str(e)}", show_alert=True)
    else:
        await callback.answer("No thumbnail to delete!", show_alert=True)

# Total stats command (owner only)
@app.on_message(filters.command("total") & filters.user(Config.OWNER_ID))
async def total_command(client, message: Message):
    stats = await db.get_stats()
    
    text = f"""📈 **Bot Statistics**

👥 **Users:**
• Total Users: {stats['total_users']}

📊 **Activity:**
• Total Downloads: {stats['total_downloads']}
• Total Uploads: {stats['total_uploads']}

⚙️ **Bot Info:**
• Speed: 500 MB/s
• Max Size: 4 GB
• Cooldown: {COOLDOWN_TIME} seconds ({format_time(COOLDOWN_TIME)})
• Status: ✅ Online

**Developer:** {Config.DEVELOPER}
**Updates:** {Config.UPDATE_CHANNEL}"""
    
    await message.reply_text(text)

# Broadcast (owner only)
@app.on_message(filters.command("broadcast") & filters.user(Config.OWNER_ID))
async def broadcast_command(client, message: Message):
    if not message.reply_to_message:
        await message.reply_text("❌ Reply to a message to broadcast!")
        return
    
    users = await db.get_all_users()
    broadcast_msg = message.reply_to_message
    
    success = 0
    failed = 0
    status_msg = await message.reply_text("📢 Broadcasting...")
    
    for user in users:
        try:
            await broadcast_msg.copy(user['user_id'])
            success += 1
            await asyncio.sleep(0.05)
        except:
            failed += 1
    
    await status_msg.edit_text(
        f"✅ **Broadcast Complete!**\n\n"
        f"Success: {success}\nFailed: {failed}"
    )

# Run bot
if __name__ == "__main__":
    print("=" * 50)
    print("🚀 URL Uploader Bot Starting...")
    print(f"👨‍💻 Developer: {Config.DEVELOPER}")
    print(f"📢 Updates: {Config.UPDATE_CHANNEL}")
    print(f"⚡ Speed: 500 MB/s")
    print(f"⏱️ Cooldown: {format_time(COOLDOWN_TIME)}")
    print("=" * 50)
    app.run()
