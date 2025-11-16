import os
import sys
import subprocess
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from pyrogram.enums import ParseMode
from config import Config
from database import db
from downloader import downloader
from helpers import (
    Progress, humanbytes, is_url, is_magnet, 
    is_video_file, get_file_extension, sanitize_filename
)
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

# Random emojis for reactions (expanded list)
REACTION_EMOJIS = [
    "❤️", "🥰", "🔥", "💋", "😍", "😘", "☺️", 
    "👍", "🎉", "👏", "⚡", "✨", "💯", "🚀",
    "😂", "🤗", "😎", "🤩", "💪", "🙌", "💖",
    "🌟", "😊", "💝", "🎊", "🥳", "😁", "💕"
]

# Welcome image URL
WELCOME_IMAGE = "https://ar-hosting.pages.dev/1762658234858.jpg"

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

async def add_reaction(message: Message):
    """
    Attempt to add a random reaction to a message.
    NOTE: This will NOT work for bot accounts, only for userbots.
    The function is included for compatibility if you convert to userbot later.
    """
    # Skip if media_group_id exists (albums/grouped media)
    if message.media_group_id:
        return
    
    try:
        message_id = message.id
        chat_id = message.chat.id
        
        # Select random emoji from list
        random_emoji = random.choice(REACTION_EMOJIS)
        
        # Attempt to react (will fail for bots)
        await message.react(emoji=random_emoji, big=True)
        
    except Exception as e:
        # Silently fail - reactions don't work for bots
        # Uncomment below to see errors in logs
        # print(f"Reaction failed: {e}")
        pass

# Start command - Auto-filter style with image (REPLY TO USER MESSAGE)
@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    await db.add_user(user_id, username, first_name)
    
    # Try to add reaction
    await add_reaction(message)
    
    text = Config.START_MESSAGE.format(
        name=first_name,
        dev=Config.DEVELOPER,
        channel=Config.UPDATE_CHANNEL
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📚 Help", callback_data="help"),
         InlineKeyboardButton("ℹ️ About", callback_data="about")],
        [InlineKeyboardButton("📢 Updates Channel", url=Config.UPDATE_CHANNEL)]
    ])
    
    # Send with photo AS REPLY to user's message
    try:
        await message.reply_photo(
            photo=WELCOME_IMAGE,
            caption=text,
            reply_markup=keyboard,
            quote=True  # This makes it a reply with highlight
        )
    except:
        # Fallback if image fails
        await message.reply_text(
            text, 
            reply_markup=keyboard, 
            disable_web_page_preview=True,
            quote=True  # This makes it a reply with highlight
        )

# Restart command (OWNER ONLY) - Restarts bot and broadcasts notification
@app.on_message(filters.command("restart") & filters.user(Config.OWNER_ID))
async def restart_command(client, message: Message):
    await add_reaction(message)
    
    restart_msg = await message.reply_text("🔄 **Restarting bot...**\n\nPlease wait...")
    
    try:
        # Get all users for broadcast
        users = await db.get_all_users()
        
        broadcast_text = "⚡ **URL Uploader Bot is restarted...**\n\nBot is now back online!"
        
        success = 0
        failed = 0
        
        # Broadcast to all users
        for user in users:
            try:
                await client.send_message(
                    chat_id=user['user_id'],
                    text=broadcast_text
                )
                success += 1
                await asyncio.sleep(0.05)  # Rate limiting
            except:
                failed += 1
        
        # Send restart summary to owner
        await restart_msg.edit_text(
            f"✅ **Broadcast Complete!**\n\n"
            f"✅ Sent: {success}\n"
            f"❌ Failed: {failed}\n\n"
            f"🔄 **Restarting now...**"
        )
        
        await asyncio.sleep(1)
        
        # Cleanup before restart
        for user_id, task in list(user_tasks.items()):
            filepath = task.get('filepath')
            if filepath:
                try:
                    downloader.cleanup(filepath)
                except:
                    pass
        user_tasks.clear()
        
        # Restart using subprocess (non-blocking)
        import subprocess
        subprocess.Popen([sys.executable] + sys.argv)
        
        # Exit current process
        sys.exit(0)
        
    except Exception as e:
        await restart_msg.edit_text(
            f"❌ **Restart Failed!**\n\n"
            f"**Error:** {str(e)}"
        )

# Help command
@app.on_callback_query(filters.regex("^help$"))
async def help_callback(client, callback: CallbackQuery):
    text = Config.HELP_MESSAGE.format(
        dev=Config.DEVELOPER,
        channel=Config.UPDATE_CHANNEL
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="back_start")]
    ])
    
    try:
        await callback.message.edit_caption(caption=text, reply_markup=keyboard)
    except:
        await callback.message.edit_text(text, reply_markup=keyboard)

@app.on_message(filters.command("help") & filters.private)
async def help_command(client, message: Message):
    await add_reaction(message)
    
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
    
    try:
        await callback.message.edit_caption(caption=text, reply_markup=keyboard)
    except:
        await callback.message.edit_text(text, reply_markup=keyboard)

@app.on_message(filters.command("about") & filters.private)
async def about_command(client, message: Message):
    await add_reaction(message)
    
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
    await add_reaction(message)
    
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
• Speed: Up to 500 MB/s
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
    await add_reaction(message)
    
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
• Speed: Up to 500 MB/s
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
        [InlineKeyboardButton("📢 Updates Channel", url=Config.UPDATE_CHANNEL)]
    ])
    
    # Try to edit caption first, fallback to text
    try:
        await callback.message.edit_caption(caption=text, reply_markup=keyboard)
    except Exception:
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except Exception as e:
            print(f"Error in back_start: {e}")
            await callback.answer("Error going back. Use /start", show_alert=True)

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
    upload_type = data.split('_')[1]  # doc or original
    
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
            f"⚡ **Powered by:** {Config.DEVELOPER}"
        )
        
        # Progress tracker
        progress = Progress(client, callback.message)
        
        if upload_type == 'doc':
            # Upload as document
            await client.send_document(
                chat_id=callback.message.chat.id,
                document=filepath,
                caption=caption,
                thumb=thumbnail,
                progress=progress.progress_callback,
                progress_args=("Uploading",)
            )
        else:  # original
            # Auto-detect and upload in original format
            ext = get_file_extension(filepath).lower()
            image_exts = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'tiff']
            
            if ext in image_exts:
                await client.send_photo(
                    chat_id=callback.message.chat.id,
                    photo=filepath,
                    caption=caption,
                    progress=progress.progress_callback,
                    progress_args=("Uploading",)
                )
            elif is_video_file(filepath):
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
            else:
                # Fallback to document
                await client.send_document(
                    chat_id=callback.message.chat.id,
                    document=filepath,
                    caption=caption,
                    thumb=thumbnail,
                    progress=progress.progress_callback,
                    progress_args=("Uploading",)
                )
        
        await db.update_stats(user_id, upload=True)
        await db.log_action(user_id, "upload", filepath)
        
        # Delete progress message
        try:
            await callback.message.delete()
        except:
            pass
        
        # Set cooldown after successful upload
        user_cooldowns[user_id] = time.time()
        
        # Success message with cooldown
        remaining = get_remaining_time(user_id)
        time_str = format_time(remaining)
        
        success_msg = await client.send_message(
            callback.message.chat.id,
            f"✅ **Upload Complete!**\n\n"
            f"⏳ You can send new task after **{time_str}**"
        )
        
        # Start cooldown refresh task
        asyncio.create_task(cooldown_refresh_message(client, success_msg, user_id))
        
        # Log to channel
        try:
            upload_type_name = 'Original' if upload_type == 'original' else 'Document'
            
            await client.send_message(
                Config.LOG_CHANNEL,
                f"📤 **New Upload**\n\n"
                f"👤 User: {callback.from_user.mention}\n"
                f"📁 File: `{filename}`\n"
                f"💾 Size: {humanbytes(filesize)}\n"
                f"📊 Type: {upload_type_name}"
            )
        except:
            pass
        
    except Exception as e:
        error_msg = str(e)
        await callback.message.edit_text(
            f"❌ **Upload Failed!**\n\n"
            f"**Error:** {error_msg[:200]}"
        )
        print(f"Upload error for user {user_id}: {error_msg}")
    
    finally:
        downloader.cleanup(filepath)
        if user_id in user_tasks:
            del user_tasks[user_id]

async def cooldown_refresh_message(client, message, user_id):
    """Refresh the cooldown message every 10 seconds"""
    last_text = ""
    consecutive_errors = 0
    max_consecutive_errors = 3
    
    try:
        while True:
            remaining = get_remaining_time(user_id)
            
            if remaining <= 0:
                # Cooldown finished
                try:
                    await message.edit_text(
                        "✅ **Upload Complete!**\n\n"
                        "🚀 **You can send new task now!**"
                    )
                except Exception:
                    pass
                break
            
            # Create new message text
            time_str = format_time(remaining)
            new_text = (
                f"✅ **Upload Complete!**\n\n"
                f"⏳ You can send new task after **{time_str}**"
            )
            
            # Only update if text changed
            if new_text != last_text:
                try:
                    await message.edit_text(new_text)
                    last_text = new_text
                    consecutive_errors = 0
                except Exception as e:
                    consecutive_errors += 1
                    error_str = str(e).lower()
                    
                    # Stop if message was deleted or too many errors
                    if 'not found' in error_str or consecutive_errors >= max_consecutive_errors:
                        break
            
            await asyncio.sleep(10)
            
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"Cooldown refresh error: {e}")

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
            f"📁 Current: `{filename}`\n\n"
            f"Type the new filename (with extension) and send:"
        )
        await callback.answer("Type new filename and send", show_alert=False)
        
    elif data == "rename_skip":
        # Skip rename, show upload options
        user_tasks[user_id]['waiting_rename'] = False
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Upload as Original", callback_data="upload_original")],
            [InlineKeyboardButton("📁 Upload as Document", callback_data="upload_doc")]
        ])
        
        await callback.message.edit_text(
            "**Choose upload type:**\n\n"
            "How do you want to upload this file?",
            reply_markup=keyboard
        )
        await callback.answer()

# Handle text input (URL or rename)
@app.on_message(filters.text & filters.private & ~filters.command(["start", "help", "about", "status", "settings", "setname", "setcaption", "clearsettings", "showthumb", "total", "broadcast", "cancel", "ping", "restart"]))
async def handle_text_input(client, message: Message):
    user_id = message.from_user.id
    
    # Try to add reaction
    await add_reaction(message)
    
    # Check if waiting for rename
    if user_id in user_tasks and user_tasks[user_id].get('waiting_rename'):
        new_name = sanitize_filename(message.text.strip())
        filepath = user_tasks[user_id]['filepath']
        
        # Create new path with new name
        new_path = os.path.join(os.path.dirname(filepath), new_name)
        
        try:
            # Rename file
            if os.path.exists(filepath):
                os.rename(filepath, new_path)
                user_tasks[user_id]['filepath'] = new_path
                user_tasks[user_id]['waiting_rename'] = False
                
                # Show upload options
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📤 Upload as Original", callback_data="upload_original")],
                    [InlineKeyboardButton("📁 Upload as Document", callback_data="upload_doc")]
                ])
                
                await message.reply_text(
                    f"✅ **Renamed to:** `{new_name}`\n\n"
                    f"**Choose upload type:**",
                    reply_markup=keyboard
                )
            else:
                await message.reply_text("❌ **Error:** File not found!")
                if user_id in user_tasks:
                    del user_tasks[user_id]
        except Exception as e:
            await message.reply_text(f"❌ **Rename failed:** {str(e)}")
        return
    
    # Check if it's a URL or magnet
    url = message.text.strip()
    if not (is_url(url) or is_magnet(url)):
        return
    
    # Check cooldown
    remaining = get_remaining_time(user_id)
    if remaining > 0:
        time_str = format_time(remaining)
        await message.reply_text(
            f"⏳ **Please wait!**\n\n"
            f"You can send new task after **{time_str}**"
        )
        return
    
    # Process as download
    await process_download(client, message, url)

# Handle torrent files and any documents
@app.on_message(filters.document & filters.private)
async def handle_document(client, message: Message):
    user_id = message.from_user.id
    
    # Try to add reaction
    await add_reaction(message)
    
    # Check cooldown
    remaining = get_remaining_time(user_id)
    if remaining > 0:
        time_str = format_time(remaining)
        await message.reply_text(
            f"⏳ **Please wait!**\n\n"
            f"You can send new task after **{time_str}**"
        )
        return
    
    # Check if it's a torrent file
    if message.document and message.document.file_name.endswith('.torrent'):
        status_msg = await message.reply_text("📥 **Downloading torrent file...**")
        try:
            torrent_path = await message.download()
            await status_msg.delete()
            await process_download(client, message, torrent_path)
        except Exception as e:
            await status_msg.edit_text(f"❌ **Error downloading torrent:** {str(e)}")
    else:
        # Handle regular file upload
        await handle_direct_file_upload(client, message)

# Handle any video files sent directly
@app.on_message(filters.video & filters.private)
async def handle_video(client, message: Message):
    user_id = message.from_user.id
    
    # Try to add reaction
    await add_reaction(message)
    
    # Check cooldown
    remaining = get_remaining_time(user_id)
    if remaining > 0:
        time_str = format_time(remaining)
        await message.reply_text(
            f"⏳ **Please wait!**\n\n"
            f"You can send new task after **{time_str}**"
        )
        return
    
    await handle_direct_file_upload(client, message)

# Handle any audio files sent directly
@app.on_message(filters.audio & filters.private)
async def handle_audio(client, message: Message):
    user_id = message.from_user.id
    
    # Try to add reaction
    await add_reaction(message)
    
    # Check cooldown
    remaining = get_remaining_time(user_id)
    if remaining > 0:
        time_str = format_time(remaining)
        await message.reply_text(
            f"⏳ **Please wait!**\n\n"
            f"You can send new task after **{time_str}**"
        )
        return
    
    await handle_direct_file_upload(client, message)

# Handle direct file uploads (not downloads)
async def handle_direct_file_upload(client, message: Message):
    """Handle files sent directly to the bot"""
    user_id = message.from_user.id
    
    await db.add_user(user_id, message.from_user.username, message.from_user.first_name)
    
    status_msg = await message.reply_text("📥 **Downloading file from Telegram...**")
    
    try:
        # Download the file
        filepath = await message.download(file_name=f"{Config.DOWNLOAD_DIR}/{message.document.file_name if message.document else message.video.file_name if message.video else message.audio.file_name if message.audio else f'file_{user_id}_{int(time.time())}'}")
        
        await status_msg.delete()
        
        # Get file info
        filename = os.path.basename(filepath)
        filesize = os.path.getsize(filepath) if os.path.isfile(filepath) else 0
        
        # Store task for rename
        user_tasks[user_id] = {
            'filepath': filepath,
            'url': 'direct_upload',
            'waiting_rename': False,
            'is_direct_upload': True
        }
        
        # Ask if user wants to rename
        text = (
            f"✅ **File Received!**\n\n"
            f"📁 **File:** `{filename}`\n"
            f"💾 **Size:** {humanbytes(filesize)}\n\n"
            f"Do you want to rename this file before re-uploading?"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ Rename Now", callback_data="rename_now")],
            [InlineKeyboardButton("⏭️ Skip Rename", callback_data="rename_skip")]
        ])
        
        await message.reply_text(text, reply_markup=keyboard)
        
        await db.update_stats(user_id, download=True)
        await db.log_action(user_id, "direct_upload", filename)
        
        # Log to channel
        try:
            await client.send_message(
                Config.LOG_CHANNEL,
                f"📤 **Direct File Upload**\n\n"
                f"👤 User: {message.from_user.mention}\n"
                f"📁 File: `{filename}`\n"
                f"💾 Size: {humanbytes(filesize)}\n"
                f"📊 Type: Direct Upload"
            )
        except:
            pass
        
    except Exception as e:
        await status_msg.edit_text(
            f"❌ **Error:** {str(e)[:300]}\n\n"
            f"Failed to process your file."
        )
        await db.log_action(user_id, "error", str(e))

# Download processing function
async def process_download(client, message: Message, url):
    user_id = message.from_user.id
    
    await db.add_user(user_id, message.from_user.username, message.from_user.first_name)
    
    # Start download
    status_msg = await message.reply_text(
        "🔄 **Processing your request...**\n\n"
        "Starting download..."
    )
    
    try:
        # Download with progress
        progress = Progress(client, status_msg)
        filepath, error = await downloader.download(
            url, 
            progress_callback=progress.progress_callback
        )
        
        if error:
            await status_msg.edit_text(
                f"❌ **Download Failed!**\n\n"
                f"**Error:** {error}\n\n"
                f"Please check the URL and try again."
            )
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
            f"💾 **Size:** {humanbytes(filesize)}\n\n"
            f"Do you want to rename this file?"
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
        await status_msg.edit_text(
            f"❌ **Error:** {str(e)[:300]}\n\n"
            f"Something went wrong. Please try again."
        )
        await db.log_action(user_id, "error", str(e))

# Settings commands
@app.on_message(filters.command("setname") & filters.private)
async def setname_command(client, message: Message):
    await add_reaction(message)
    
    user_id = message.from_user.id
    if len(message.command) < 2:
        await message.reply_text(
            "**Usage:** `/setname filename.ext`\n\n"
            "**Example:** `/setname movie.mp4`"
        )
        return
    
    filename = sanitize_filename(" ".join(message.command[1:]))
    if user_id not in user_settings:
        user_settings[user_id] = {}
    user_settings[user_id]['filename'] = filename
    
    await message.reply_text(f"✅ **Filename set to:** `{filename}`")

@app.on_message(filters.command("setcaption") & filters.private)
async def setcaption_command(client, message: Message):
    await add_reaction(message)
    
    user_id = message.from_user.id
    if len(message.command) < 2:
        await message.reply_text(
            "**Usage:** `/setcaption Your caption here`\n\n"
            "This will be used for all your uploads."
        )
        return
    
    caption = message.text.split(None, 1)[1]
    if user_id not in user_settings:
        user_settings[user_id] = {}
    user_settings[user_id]['caption'] = caption
    
    await message.reply_text("✅ **Caption set successfully!**")

@app.on_message(filters.command("clearsettings") & filters.private)
async def clearsettings_command(client, message: Message):
    await add_reaction(message)
    
    user_id = message.from_user.id
    if user_id in user_settings:
        user_settings[user_id] = {}
    await message.reply_text("✅ **All settings cleared!**")

# Thumbnail handler
@app.on_message(filters.photo & filters.private)
async def handle_thumbnail(client, message: Message):
    await add_reaction(message)
    
    user_id = message.from_user.id
    
    status_msg = await message.reply_text("📥 Downloading thumbnail...")
    
    try:
        thumb_path = await message.download(
            file_name=f"{Config.DOWNLOAD_DIR}/thumb_{user_id}.jpg"
        )
        
        if user_id not in user_settings:
            user_settings[user_id] = {}
        user_settings[user_id]['thumbnail'] = thumb_path
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑️ Delete Thumbnail", callback_data="delete_thumb")]
        ])
        
        await status_msg.edit_text(
            "✅ **Thumbnail saved successfully!**\n\n"
            "This will be used for all video/document uploads.",
            reply_markup=keyboard
        )
    except Exception as e:
        await status_msg.edit_text(f"❌ **Error:** {str(e)}")

# Show thumbnail command
@app.on_message(filters.command("showthumb") & filters.private)
async def showthumb_command(client, message: Message):
    await add_reaction(message)
    
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
    await add_reaction(message)
    
    stats = await db.get_stats()
    
    text = f"""📈 **Bot Statistics**

👥 **Users:**
• Total Users: {stats['total_users']}

📊 **Activity:**
• Total Downloads: {stats['total_downloads']}
• Total Uploads: {stats['total_uploads']}

⚙️ **Bot Info:**
• Speed: Up to 500 MB/s
• Max Size: 4 GB
• Cooldown: {COOLDOWN_TIME} seconds ({format_time(COOLDOWN_TIME)})
• Status: ✅ Online

**Developer:** {Config.DEVELOPER}
**Updates:** {Config.UPDATE_CHANNEL}"""
    
    await message.reply_text(text)

# Broadcast (owner only)
@app.on_message(filters.command("broadcast") & filters.user(Config.OWNER_ID))
async def broadcast_command(client, message: Message):
    await add_reaction(message)
    
    if not message.reply_to_message:
        await message.reply_text("❌ **Reply to a message to broadcast!**")
        return
    
    users = await db.get_all_users()
    broadcast_msg = message.reply_to_message
    
    success = 0
    failed = 0
    blocked = 0
    deleted = 0
    
    status_msg = await message.reply_text("📢 **Broadcasting...**\n\nStarting...")
    
    for idx, user in enumerate(users):
        try:
            await broadcast_msg.copy(user['user_id'])
            success += 1
        except Exception as e:
            failed += 1
            error_str = str(e).lower()
            if 'blocked' in error_str:
                blocked += 1
            elif 'deleted' in error_str or 'deactivated' in error_str:
                deleted += 1
        
        # Update status every 50 users
        if (idx + 1) % 50 == 0:
            try:
                await status_msg.edit_text(
                    f"📢 **Broadcasting...**\n\n"
                    f"✅ Success: {success}\n"
                    f"❌ Failed: {failed}\n"
                    f"🚫 Blocked: {blocked}\n"
                    f"👻 Deleted: {deleted}\n"
                    f"📊 Progress: {idx + 1}/{len(users)}"
                )
            except:
                pass
        
        await asyncio.sleep(0.05)  # Rate limiting
    
    await status_msg.edit_text(
        f"✅ **Broadcast Complete!**\n\n"
        f"✅ **Success:** {success}\n"
        f"❌ **Failed:** {failed}\n"
        f"🚫 **Blocked:** {blocked}\n"
        f"👻 **Deleted:** {deleted}\n"
        f"📊 **Total:** {len(users)}"
    )

# Cancel command - Cancel current task
@app.on_message(filters.command("cancel") & filters.private)
async def cancel_command(client, message: Message):
    await add_reaction(message)
    
    user_id = message.from_user.id
    
    if user_id in user_tasks:
        task = user_tasks[user_id]
        filepath = task.get('filepath')
        
        # Clean up file
        if filepath:
            downloader.cleanup(filepath)
        
        # Remove task
        del user_tasks[user_id]
        
        await message.reply_text(
            "✅ **Task cancelled successfully!**\n\n"
            "You can send a new URL/magnet link."
        )
    else:
        await message.reply_text(
            "❌ **No active task to cancel!**\n\n"
            "Send a URL or magnet link to start downloading."
        )

# Ping command - Check bot status
@app.on_message(filters.command("ping") & filters.private)
async def ping_command(client, message: Message):
    await add_reaction(message)
    
    start = time.time()
    reply = await message.reply_text("🏓 **Pinging...**")
    end = time.time()
    
    ms = (end - start) * 1000
    
    await reply.edit_text(
        f"🏓 **Pong!**\n\n"
        f"⚡ **Response Time:** `{ms:.2f}ms`\n"
        f"✅ **Status:** Online"
    )

# Error handler for unknown commands
@app.on_message(filters.command(["unknown"]) & filters.private)
async def unknown_command(client, message: Message):
    await add_reaction(message)
    
    await message.reply_text(
        "❓ **Unknown command!**\n\n"
        "Use /help to see available commands."
    )

# Startup message
async def startup():
    """Send startup notification"""
    try:
        await app.send_message(
            Config.OWNER_ID,
            "🚀 **Bot Started Successfully!**\n\n"
            f"⚡ Speed: Up to 500 MB/s\n"
            f"💾 Max Size: 4 GB\n"
            f"⏱️ Cooldown: {format_time(COOLDOWN_TIME)}\n"
            f"✅ Status: Online\n\n"
            f"⚠️ **Note:** Reactions are enabled but will only work if converted to userbot."
        )
    except Exception as e:
        print(f"Startup notification failed: {e}")

# Shutdown handler
async def shutdown():
    """Cleanup on shutdown"""
    print("🛑 Bot shutting down...")
    
    # Cleanup all active downloads
    for user_id, task in list(user_tasks.items()):
        filepath = task.get('filepath')
        if filepath:
            downloader.cleanup(filepath)
    
    user_tasks.clear()
    
    try:
        await app.send_message(
            Config.OWNER_ID,
            "🛑 **Bot Stopped!**\n\n"
            "The bot has been shut down."
        )
    except:
        pass
    
    print("✅ Cleanup complete!")

# Run bot
if __name__ == "__main__":
    print("=" * 60)
    print("🚀 URL Uploader Bot Starting...")
    print(f"👨‍💻 Developer: {Config.DEVELOPER}")
    print(f"📢 Updates: {Config.UPDATE_CHANNEL}")
    print(f"⚡ Speed: Up to 500 MB/s")
    print(f"💾 Max Size: 4 GB")
    print(f"⏱️ Cooldown: {format_time(COOLDOWN_TIME)}")
    print(f"😊 Reactions: Enabled (28 emojis)")
    print("⚠️  Note: Reactions won't work for bot accounts")
    print("=" * 60)
    
    try:
        # Start bot
        app.start()
        print(f"✅ Bot started as @{app.me.username}")
        
        # Send startup notification
        loop = asyncio.get_event_loop()
        loop.run_until_complete(startup())
        
        # Keep bot running
        from pyrogram import idle
        idle()
        
    except KeyboardInterrupt:
        print("\n⚠️ Keyboard interrupt received!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
    finally:
        # Cleanup on exit
        loop = asyncio.get_event_loop()
        loop.run_until_complete(shutdown())
        app.stop()
        print("👋 Bot stopped successfully!")
