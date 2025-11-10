import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pyrogram.errors import FloodWait, MessageNotModified
from config import Config
from database import db
from downloader import downloader
from helpers import (
    humanbytes, is_url, is_magnet_link, is_torrent_file,
    Progress, TorrentProgress, sanitize_filename, 
    validate_file_size, get_file_extension
)
import time

# Initialize bot
app = Client(
    "url_uploader_bot",
    api_id=Config.APP_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

# User settings storage (in memory)
user_settings = {}

# Active downloads tracker
active_downloads = {}

# Start command
@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    await db.add_user(user_id, username, first_name)
    await db.log_action(user_id, "start", "User started the bot")
    
    text = (
        f"👋 **Welcome {first_name}!**\n\n"
        "I'm a powerful URL uploader bot that can:\n"
        "• Download files from any URL\n"
        "• Download videos from YouTube, Instagram, TikTok, etc.\n"
        "• Support torrents (magnet links & .torrent files)\n"
        "• Upload files up to 4GB to Telegram\n"
        "• Real-time progress with speed and ETA\n\n"
        "**How to use:**\n"
        "Just send me any URL and I'll download and upload it for you!\n\n"
        "**Commands:**\n"
        "/help - Show help message\n"
        "/about - About this bot\n"
        "/settings - Configure caption, filename, thumbnail\n"
        "/status - Check your stats\n\n"
        "Send a URL to get started! 🚀"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📚 Help", callback_data="help"),
         InlineKeyboardButton("ℹ️ About", callback_data="about")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings")]
    ])
    
    await message.reply_text(text, reply_markup=keyboard)

# Help command
@app.on_message(filters.command("help"))
async def help_command(client, message: Message):
    text = (
        "📚 **Help & Usage**\n\n"
        "**Basic Usage:**\n"
        "• Send any HTTP/HTTPS URL to download\n"
        "• Send YouTube, Instagram, TikTok URLs\n"
        "• Send magnet links (magnet:?...)\n"
        "• Send .torrent file links\n"
        "• I'll download and upload to Telegram\n\n"
        "**Settings:**\n"
        "Use /settings to customize:\n"
        "• Custom filename\n"
        "• Custom caption\n"
        "• Custom thumbnail (send photo)\n\n"
        "**Commands:**\n"
        "/start - Start the bot\n"
        "/help - This message\n"
        "/about - About the bot\n"
        "/settings - Configure settings\n"
        "/status - Your download stats\n"
        "/cancel - Cancel active download\n"
        "/total - Bot statistics (owner only)\n"
        "/broadcast - Broadcast message (owner only)\n\n"
        "**Limits:**\n"
        "• Max file size: 4GB\n"
        "• Speed: 10 MB/s\n"
        "• Format: Any file type supported"
    )
    await message.reply_text(text)

# About command
@app.on_message(filters.command("about"))
async def about_command(client, message: Message):
    text = (
        "ℹ️ **About URL Uploader Bot**\n\n"
        "**Version:** 2.0\n"
        "**Developer:** @YourUsername\n\n"
        "**Features:**\n"
        "✅ Direct URL downloads\n"
        "✅ YouTube video downloads\n"
        "✅ Instagram, TikTok support\n"
        "✅ Torrent downloads (magnet links)\n"
        "✅ Real-time progress tracking\n"
        "✅ Custom thumbnails & captions\n"
        "✅ Speed limiting (10 MB/s)\n"
        "✅ Up to 4GB file support\n\n"
        "**Technology:**\n"
        "• Pyrogram - Telegram API\n"
        "• yt-dlp - Video downloads\n"
        "• libtorrent - Torrent support\n"
        "• aiohttp - HTTP downloads\n"
        "• MongoDB - Data storage\n\n"
        "Made with ❤️ for the community!"
    )
    await message.reply_text(text)

# Status command
@app.on_message(filters.command("status"))
async def status_command(client, message: Message):
    user_id = message.from_user.id
    user_data = await db.get_user(user_id)
    
    if user_data:
        text = (
            "📊 **Your Statistics**\n\n"
            f"**User ID:** `{user_id}`\n"
            f"**Username:** @{user_data.get('username', 'N/A')}\n"
            f"**Joined:** {user_data.get('joined_date').strftime('%Y-%m-%d')}\n"
            f"**Total Downloads:** {user_data.get('total_downloads', 0)}\n"
            f"**Total Uploads:** {user_data.get('total_uploads', 0)}\n"
            f"**Last Used:** {user_data.get('last_used').strftime('%Y-%m-%d %H:%M')}"
        )
    else:
        text = "No data found. Use the bot first!"
    
    await message.reply_text(text)

# Cancel command
@app.on_message(filters.command("cancel"))
async def cancel_command(client, message: Message):
    user_id = message.from_user.id
    
    if user_id in active_downloads:
        # Mark for cancellation
        active_downloads[user_id]['cancelled'] = True
        await message.reply_text("⏹️ Cancelling download...")
    else:
        await message.reply_text("❌ No active download to cancel!")

# Total stats command (owner only)
@app.on_message(filters.command("total") & filters.user(Config.OWNER_ID))
async def total_command(client, message: Message):
    stats = await db.get_stats()
    
    text = (
        "📈 **Bot Statistics**\n\n"
        f"**Total Users:** {stats['total_users']}\n"
        f"**Total Downloads:** {stats['total_downloads']}\n"
        f"**Total Uploads:** {stats['total_uploads']}\n"
        f"**Active Downloads:** {len(active_downloads)}\n\n"
        f"**Server Status:** ✅ Online\n"
        f"**Speed Limit:** 10 MB/s\n"
        f"**Max File Size:** 4 GB"
    )
    
    await message.reply_text(text)

# Broadcast command (owner only)
@app.on_message(filters.command("broadcast") & filters.user(Config.OWNER_ID))
async def broadcast_command(client, message: Message):
    if not message.reply_to_message:
        await message.reply_text("❌ Reply to a message to broadcast it!")
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
        except Exception:
            failed += 1
    
    await status_msg.edit_text(
        f"✅ **Broadcast Complete**\n\n"
        f"**Success:** {success}\n"
        f"**Failed:** {failed}"
    )

# Settings command
@app.on_message(filters.command("settings"))
async def settings_command(client, message: Message):
    user_id = message.from_user.id
    settings = user_settings.get(user_id, {})
    
    text = (
        "⚙️ **Your Settings**\n\n"
        f"**Custom Filename:** `{settings.get('filename', 'Not set')}`\n"
        f"**Custom Caption:** `{settings.get('caption', 'Not set')}`\n"
        f"**Thumbnail:** {'✅ Set' if settings.get('thumbnail') else '❌ Not set'}\n\n"
        "**To configure:**\n"
        "• `/setname <filename>` - Set custom filename\n"
        "• `/setcaption <caption>` - Set custom caption\n"
        "• Send a photo - Set thumbnail\n"
        "• `/clearsettings` - Clear all settings"
    )
    
    await message.reply_text(text)

# Set filename
@app.on_message(filters.command("setname"))
async def set_filename(client, message: Message):
    user_id = message.from_user.id
    
    if len(message.command) < 2:
        await message.reply_text("❌ Usage: `/setname filename.ext`")
        return
    
    filename = " ".join(message.command[1:])
    filename = sanitize_filename(filename)
    
    if user_id not in user_settings:
        user_settings[user_id] = {}
    user_settings[user_id]['filename'] = filename
    
    await message.reply_text(f"✅ Filename set to: `{filename}`")

# Set caption
@app.on_message(filters.command("setcaption"))
async def set_caption(client, message: Message):
    user_id = message.from_user.id
    
    if len(message.command) < 2:
        await message.reply_text("❌ Usage: `/setcaption Your caption here`")
        return
    
    caption = message.text.split(None, 1)[1]
    
    if user_id not in user_settings:
        user_settings[user_id] = {}
    user_settings[user_id]['caption'] = caption
    
    await message.reply_text("✅ Caption set successfully!")

# Clear settings
@app.on_message(filters.command("clearsettings"))
async def clear_settings(client, message: Message):
    user_id = message.from_user.id
    
    if user_id in user_settings:
        # Clean up thumbnail file if exists
        if 'thumbnail' in user_settings[user_id]:
            thumb_path = user_settings[user_id]['thumbnail']
            if os.path.exists(thumb_path):
                try:
                    os.remove(thumb_path)
                except:
                    pass
        
        user_settings[user_id] = {}
    
    await message.reply_text("✅ All settings cleared!")

# Handle photo for thumbnail
@app.on_message(filters.photo)
async def handle_thumbnail(client, message: Message):
    user_id = message.from_user.id
    
    try:
        # Download photo as thumbnail
        thumb_path = await message.download(
            file_name=f"{Config.DOWNLOAD_DIR}/thumb_{user_id}.jpg"
        )
        
        if user_id not in user_settings:
            user_settings[user_id] = {}
        
        # Remove old thumbnail if exists
        if 'thumbnail' in user_settings[user_id]:
            old_thumb = user_settings[user_id]['thumbnail']
            if os.path.exists(old_thumb):
                try:
                    os.remove(old_thumb)
                except:
                    pass
        
        user_settings[user_id]['thumbnail'] = thumb_path
        await message.reply_text("✅ Thumbnail set successfully!")
        
    except Exception as e:
        await message.reply_text(f"❌ Failed to set thumbnail: {str(e)}")

# Main URL handler
@app.on_message(filters.text & filters.private)
async def handle_url(client, message: Message):
    url = message.text.strip()
    
    # Check if it's a valid URL
    if not is_url(url):
        return
    
    user_id = message.from_user.id
    
    # Check if user already has active download
    if user_id in active_downloads:
        await message.reply_text("⚠️ You already have an active download! Use /cancel to stop it.")
        return
    
    # Add user to database
    await db.add_user(user_id, message.from_user.username, message.from_user.first_name)
    
    # Initial message
    status_msg = await message.reply_text("🔄 **Processing your request...**")
    
    # Mark download as active
    active_downloads[user_id] = {
        'cancelled': False,
        'status_msg': status_msg
    }
    
    filepath = None
    
    try:
        # Determine download type and create appropriate progress tracker
        is_torrent = is_magnet_link(url) or is_torrent_file(url)
        
        if is_torrent:
            progress = TorrentProgress(client, status_msg)
        else:
            progress = Progress(client, status_msg)
        
        # Download file
        filepath, error = await downloader.download(
            url, 
            progress_callback=progress.progress_callback
        )
        
        # Check if cancelled
        if active_downloads.get(user_id, {}).get('cancelled'):
            if filepath and os.path.exists(filepath):
                downloader.cleanup(filepath)
            await status_msg.edit_text("⏹️ **Download cancelled!**")
            return
        
        if error:
            await status_msg.edit_text(f"❌ **Error:** {error}")
            await db.log_action(user_id, "error", error)
            return
        
        # Validate file
        if not os.path.exists(filepath):
            await status_msg.edit_text("❌ **Error:** File not found after download")
            return
        
        # Check file size
        file_size = os.path.getsize(filepath)
        is_valid, msg = validate_file_size(file_size, Config.MAX_FILE_SIZE)
        
        if not is_valid:
            await status_msg.edit_text(f"❌ **Error:** {msg}")
            downloader.cleanup(filepath)
            return
        
        # Update stats
        await db.update_stats(user_id, download=True)
        await db.log_action(user_id, "download", url)
        
        # Get user settings
        settings = user_settings.get(user_id, {})
        custom_filename = settings.get('filename')
        thumbnail = settings.get('thumbnail')
        
        # Prepare caption
        filename_display = custom_filename or os.path.basename(filepath)
        default_caption = (
            f"📁 **File:** `{filename_display}`\n"
            f"💾 **Size:** {humanbytes(file_size)}\n"
            f"🔗 **Source:** Direct Download"
        )
        custom_caption = settings.get('caption', default_caption)
        
        # Rename if custom filename provided
        if custom_filename:
            new_path = os.path.join(Config.DOWNLOAD_DIR, custom_filename)
            try:
                os.rename(filepath, new_path)
                filepath = new_path
            except Exception as e:
                pass
        
        # Ask user how to upload (Document or Video)
        buttons = [
            [InlineKeyboardButton("📄 Document", callback_data=f"upload_doc:{user_id}")],
            [InlineKeyboardButton("🎬 Video", callback_data=f"upload_vid:{user_id}")]
        ]
        
        await status_msg.edit_text(
            "⚡ **Download complete!**\n\n"
            "Choose how you want to upload the file:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
        # Store file info for callback
        active_downloads[user_id]['filepath'] = filepath
        active_downloads[user_id]['thumbnail'] = thumbnail
        active_downloads[user_id]['caption'] = custom_caption
        active_downloads[user_id]['status_msg'] = status_msg
        
    except Exception as e:
        await status_msg.edit_text(f"❌ **Error:** {str(e)}")
        await db.log_action(user_id, "error", str(e))
    
# Callback query handler
@app.on_callback_query()
async def callback_handler(client, callback_query):
    data = callback_query.data
    
    if data == "help":
        await help_command(client, callback_query.message)
    elif data == "about":
        await about_command(client, callback_query.message)
    elif data == "settings":
        await settings_command(client, callback_query.message)
    
    # Handle upload choice
    elif data.startswith("upload_doc:") or data.startswith("upload_vid:"):
        uid = int(data.split(":")[1])
        if uid not in active_downloads:
            await callback_query.answer("❌ File not found or expired", show_alert=True)
            return
        
        info = active_downloads[uid]
        filepath = info['filepath']
        caption = info['caption']
        thumbnail = info['thumbnail']
        status_msg = info['status_msg']
        
        upload_progress = Progress(client, status_msg)
        
        try:
            if data.startswith("upload_doc:"):
                await client.send_document(
                    chat_id=callback_query.message.chat.id,
                    document=filepath,
                    caption=caption,
                    thumb=thumbnail,
                    progress=upload_progress.progress_callback,
                    progress_args=("Uploading",)
                )
            else:
                await client.send_video(
                    chat_id=callback_query.message.chat.id,
                    video=filepath,
                    caption=caption,
                    thumb=thumbnail,
                    progress=upload_progress.progress_callback,
                    progress_args=("Uploading",),
                    supports_streaming=True
                )
            
            # Update stats
            await db.update_stats(uid, upload=True)
            await db.log_action(uid, "upload", filepath)
            
            await status_msg.delete()
            await callback_query.message.delete()
            
        except Exception as e:
            await status_msg.edit_text(f"❌ Upload failed: {str(e)}")
        
        finally:
            if os.path.exists(filepath):
                downloader.cleanup(filepath)
            del active_downloads[uid]
        
        await callback_query.answer("✅ Upload started!")
    
    else:
        await callback_query.answer()

# Run bot
if __name__ == "__main__":
    print("🤖 Bot starting...")
    print(f"✅ Torrent support enabled")
    print(f"✅ Video download support enabled")
    print(f"✅ Progress tracking optimized")
    app.run()
