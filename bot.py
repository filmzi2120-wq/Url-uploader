import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from config import Config
from database import db
from downloader import downloader
from helpers import Progress, humanbytes, is_url
import time
import re

# Initialize bot
app = Client(
    "url_uploader_bot",
    api_id=Config.APP_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

# User settings storage (in memory)
user_settings = {}

def is_magnet_link(text):
    """Check if text is a magnet link"""
    return text.strip().startswith('magnet:?')

def is_torrent_url(text):
    """Check if text is a torrent file URL"""
    return text.strip().lower().endswith('.torrent')

# Start command
@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    # Add user to database
    await db.add_user(user_id, username, first_name)
    await db.log_action(user_id, "start", "User started the bot")
    
    text = (
        f"👋 **Welcome {first_name}!**\n\n"
        "I'm a powerful URL uploader bot that can:\n"
        "• Download files from any URL\n"
        "• Download videos from YouTube, Instagram, etc.\n"
        "• Download torrents via magnet links 🧲\n"
        "• Upload files up to 4GB to Telegram\n"
        "• Show progress with speed and ETA\n\n"
        "**How to use:**\n"
        "Just send me any URL, magnet link, or torrent file and I'll download and upload it for you!\n\n"
        "**Commands:**\n"
        "/help - Show help message\n"
        "/about - About this bot\n"
        "/settings - Configure caption, filename, thumbnail\n"
        "/status - Check your stats\n\n"
        "Send a URL or magnet link to get started! 🚀"
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
        "• Send magnet links (magnet:?xt=...)\n"
        "• Send .torrent file URLs\n"
        "• I'll download and upload to Telegram\n\n"
        "**Torrent Downloads:**\n"
        "• Magnet links are supported 🧲\n"
        "• Shows peers, download speed\n"
        "• Works with any torrent tracker\n\n"
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
        "/total - Overall bot statistics (owner only)\n"
        "/broadcast - Send message to all users (owner only)\n\n"
        "**Limits:**\n"
        "• Max file size: 4GB\n"
        "• Speed: 10 MB/s (HTTP)\n"
        "• Format: Any file type supported\n\n"
        "⚠️ **Note:** Only download legal torrents you have rights to!"
    )
    await message.reply_text(text)

# About command
@app.on_message(filters.command("about"))
async def about_command(client, message: Message):
    text = (
        "ℹ️ **About URL Uploader Bot**\n\n"
        "**Version:** 2.1 (Torrent Support)\n"
        "**Developer:** @YourUsername\n\n"
        "**Features:**\n"
        "✅ Direct URL downloads\n"
        "✅ YouTube video downloads\n"
        "✅ Instagram, TikTok support\n"
        "✅ Torrent downloads (Magnet links) 🧲\n"
        "✅ Progress tracking\n"
        "✅ Custom thumbnails\n"
        "✅ Speed limiting (10 MB/s)\n"
        "✅ Up to 4GB file support\n\n"
        "**Technology:**\n"
        "• Pyrogram for Telegram API\n"
        "• yt-dlp for video downloads\n"
        "• aiohttp for HTTP downloads\n"
        "• libtorrent for torrent downloads\n"
        "• MongoDB for data storage\n\n"
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

# Total stats command (owner only)
@app.on_message(filters.command("total") & filters.user(Config.OWNER_ID))
async def total_command(client, message: Message):
    stats = await db.get_stats()
    
    text = (
        "📈 **Bot Statistics**\n\n"
        f"**Total Users:** {stats['total_users']}\n"
        f"**Total Downloads:** {stats['total_downloads']}\n"
        f"**Total Uploads:** {stats['total_uploads']}\n\n"
        f"**Server Status:** ✅ Online\n"
        f"**Speed Limit:** 10 MB/s\n"
        f"**Max File Size:** 4 GB\n"
        f"**Torrent Support:** ✅ Enabled"
    )
    
    await message.reply_text(text)

# Broadcast command (owner only)
@app.on_message(filters.command("broadcast") & filters.user(Config.OWNER_ID))
async def broadcast_command(client, message: Message):
    if not message.reply_to_message:
        await message.reply_text("Reply to a message to broadcast it!")
        return
    
    users = await db.get_all_users()
    broadcast_msg = message.reply_to_message
    
    success = 0
    failed = 0
    
    status_msg = await message.reply_text("Broadcasting...")
    
    for user in users:
        try:
            await broadcast_msg.copy(user['user_id'])
            success += 1
            await asyncio.sleep(0.05)  # Avoid flood
        except Exception:
            failed += 1
    
    await status_msg.edit_text(
        f"✅ **Broadcast Complete**\n\n"
        f"Success: {success}\n"
        f"Failed: {failed}"
    )

# Settings command
@app.on_message(filters.command("settings"))
async def settings_command(client, message: Message):
    user_id = message.from_user.id
    settings = user_settings.get(user_id, {})
    
    text = (
        "⚙️ **Your Settings**\n\n"
        f"**Custom Filename:** {settings.get('filename', 'Not set')}\n"
        f"**Custom Caption:** {settings.get('caption', 'Not set')}\n"
        f"**Thumbnail:** {'Set ✅' if settings.get('thumbnail') else 'Not set'}\n\n"
        "To set:\n"
        "• `/setname <filename>` - Set custom filename\n"
        "• `/setcaption <caption>` - Set custom caption\n"
        "• Send a photo to set thumbnail\n"
        "• `/clearsettings` - Clear all settings"
    )
    
    await message.reply_text(text)

# Set filename
@app.on_message(filters.command("setname"))
async def set_filename(client, message: Message):
    user_id = message.from_user.id
    if len(message.command) < 2:
        await message.reply_text("Usage: `/setname filename.ext`")
        return
    
    filename = " ".join(message.command[1:])
    
    if user_id not in user_settings:
        user_settings[user_id] = {}
    user_settings[user_id]['filename'] = filename
    
    await message.reply_text(f"✅ Filename set to: `{filename}`")

# Set caption
@app.on_message(filters.command("setcaption"))
async def set_caption(client, message: Message):
    user_id = message.from_user.id
    if len(message.command) < 2:
        await message.reply_text("Usage: `/setcaption Your caption here`")
        return
    
    caption = message.text.split(None, 1)[1]
    
    if user_id not in user_settings:
        user_settings[user_id] = {}
    user_settings[user_id]['caption'] = caption
    
    await message.reply_text(f"✅ Caption set!")

# Clear settings
@app.on_message(filters.command("clearsettings"))
async def clear_settings(client, message: Message):
    user_id = message.from_user.id
    if user_id in user_settings:
        user_settings[user_id] = {}
    await message.reply_text("✅ All settings cleared!")

# Handle photo for thumbnail
@app.on_message(filters.photo)
async def handle_thumbnail(client, message: Message):
    user_id = message.from_user.id
    
    # Download photo as thumbnail
    thumb_path = await message.download(file_name=f"{Config.DOWNLOAD_DIR}/thumb_{user_id}.jpg")
    
    if user_id not in user_settings:
        user_settings[user_id] = {}
    user_settings[user_id]['thumbnail'] = thumb_path
    
    await message.reply_text("✅ Thumbnail set successfully!")

# Main URL/Magnet handler
@app.on_message(filters.text & filters.private)
async def handle_url(client, message: Message):
    url = message.text.strip()
    
    # Check if it's a URL, magnet link, or torrent
    if not (is_url(url) or is_magnet_link(url) or is_torrent_url(url)):
        return
    
    user_id = message.from_user.id
    await db.add_user(user_id, message.from_user.username, message.from_user.first_name)
    
    # Detect type
    download_type = "torrent" if (is_magnet_link(url) or is_torrent_url(url)) else "url"
    
    # Initial message
    if download_type == "torrent":
        status_msg = await message.reply_text("🧲 **Processing torrent...**\nThis may take a moment to connect to peers...")
    else:
        status_msg = await message.reply_text("🔄 **Processing your request...**")
    
    try:
        # Download file
        progress = Progress(client, status_msg)
        filepath, error = await downloader.download(url, progress_callback=progress.progress_callback)
        
        if error:
            await status_msg.edit_text(f"❌ **Error:** {error}")
            return
        
        # Update stats
        await db.update_stats(user_id, download=True)
        await db.log_action(user_id, f"download_{download_type}", url)
        
        # Get file size
        file_size = os.path.getsize(filepath)
        
        # Check if file exceeds Telegram limit
        if file_size > Config.MAX_FILE_SIZE:
            await status_msg.edit_text(
                f"❌ **Error:** File size ({humanbytes(file_size)}) exceeds 4GB limit!\n"
                "Please try a smaller file."
            )
            downloader.cleanup(filepath)
            return
        
        # Get user settings
        settings = user_settings.get(user_id, {})
        custom_filename = settings.get('filename')
        custom_caption = settings.get('caption', f"📁 **File:** {os.path.basename(filepath)}\n💾 **Size:** {humanbytes(file_size)}")
        thumbnail = settings.get('thumbnail')
        
        # Add torrent emoji to caption if it's a torrent download
        if download_type == "torrent":
            custom_caption = f"🧲 {custom_caption}"
        
        # Rename if custom filename provided
        if custom_filename:
            new_path = os.path.join(Config.DOWNLOAD_DIR, custom_filename)
            os.rename(filepath, new_path)
            filepath = new_path
        
        # Upload to Telegram
        await status_msg.edit_text("⬆️ **Uploading to Telegram...**")
        
        progress_upload = Progress(client, status_msg)
        
        # Send as document
        await client.send_document(
            chat_id=message.chat.id,
            document=filepath,
            caption=custom_caption,
            thumb=thumbnail,
            progress=progress_upload.progress_callback,
            progress_args=("Uploading",)
        )
        
        # Update stats
        await db.update_stats(user_id, upload=True)
        await db.log_action(user_id, "upload", filepath)
        
        # Delete status message
        await status_msg.delete()
        
        # Log to channel
        try:
            log_text = (
                f"📤 **New Upload**\n\n"
                f"**User:** {message.from_user.mention}\n"
                f"**File:** {os.path.basename(filepath)}\n"
                f"**Size:** {humanbytes(file_size)}\n"
                f"**Type:** {download_type.upper()}\n"
            )
            if download_type == "torrent":
                log_text += f"**Magnet:** `{url[:100]}...`"
            else:
                log_text += f"**URL:** `{url}`"
                
            await client.send_message(Config.LOG_CHANNEL, log_text)
        except Exception:
            pass
        
    except Exception as e:
        await status_msg.edit_text(f"❌ **Error:** {str(e)}")
        await db.log_action(user_id, "error", str(e))
    
    finally:
        # Cleanup
        if 'filepath' in locals():
            downloader.cleanup(filepath)

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
    
    await callback_query.answer()

# Run bot
if __name__ == "__main__":
    print("🤖 Bot starting...")
    print("✅ Torrent support enabled")
    app.run()
