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
import libs

# For custom reactions
class ReturnCommand(Exception):
    pass

class ReactionType:
    def __init__(self, type, emoji):
        self.type = type
        self.emoji = emoji  

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
WELCOME_IMAGE = "https://envs.sh/xSn.gif"  

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
    Add a random reaction to a message using custom method.
    """
    try:
        # Check for media_group_id
        msgg = str(message)
        if 'media_group_id' in str(msgg):
            raise ReturnCommand
        
        message_id = message.message_id
        chat_id = str(message.chat.id)
        
        # Select random emoji from list
        a = ["❤️", "🥰", "🔥", "💋", "😍", "😘", "☺️"]
        b = random.choice(a)
        
        # Set reaction using custom bot method
        await message._client.set_reaction(
            chat_id=chat_id, 
            message_id=message_id, 
            reaction=[ReactionType(type="emoji", emoji=b)], 
            is_big=True
        )
        
    except ReturnCommand:
        return
    except Exception as e:  
        # Silently fail - reactions might not always work
        pass  

# Start command - Auto-filter style with ANIMATED GIF (REPLY TO USER MESSAGE)  
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
    
    # Send with ANIMATED GIF AS REPLY to user's message  
    try:  
        # Use send_animation instead of send_photo to keep GIF animated  
        await message.reply_animation(  
            animation=WELCOME_IMAGE,  
            caption=text,  
            reply_markup=keyboard,  
            parse_mode="html",  
            quote=True  
        )  
    except Exception as e:  
        # Fallback if animation fails - try as document  
        try:  
            await message.reply_document(  
                document=WELCOME_IMAGE,  
                caption=text,  
                reply_markup=keyboard,  
                quote=True  
            )  
        except:  
            # Final fallback - text only  
            await message.reply_text(  
                text,   
                reply_markup=keyboard,   
                disable_web_page_preview=True,  
                quote=True  
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

# Back to start - FIXED to show animated GIF  
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
    
    # Delete old message and send new one with animation to keep GIF animated  
    try:  
        await callback.message.delete()  
        
        await client.send_animation(  
            chat_id=callback.message.chat.id,  
            animation=WELCOME_IMAGE,  
            caption=text,  
            reply_markup=keyboard  
        )  
        await callback.answer()  
        
    except Exception as e:  
        # Fallback: try editing if deletion fails  
        try:  
            await callback.message.edit_caption(caption=text, reply_markup=keyboard)  
        except Exception:  
            try:  
                await callback.message.edit_text(text, reply_markup=keyboard)  
            except Exception as e:  
                print(f"Error in back_start: {e}")  
                await callback.answer("Error going back. Use /start", show_alert=True)  

# [REMAINING CODE CONTINUES WITH ALL OTHER HANDLERS...]
# Due to length limits, the rest of the code remains exactly the same
# Just replace the add_reaction function at the top with the new implementation

# Run bot  
if __name__ == "__main__":  
    print("=" * 60)  
    print("🚀 URL Uploader Bot Starting...")  
    print(f"👨‍💻 Developer: {Config.DEVELOPER}")  
    print(f"📢 Updates: {Config.UPDATE_CHANNEL}")  
    print(f"⚡ Speed: Up to 500 MB/s")  
    print(f"💾 Max Size: 4 GB")  
    print(f"⏱️ Cooldown: {format_time(COOLDOWN_TIME)}")  
    print(f"😊 Reactions: Enabled (Custom Implementation)")  
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
