import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram API credentials
    APP_ID = int(os.environ.get("APP_ID", "20288994"))
    API_HASH = os.environ.get("API_HASH", "d702614912f1ad370a0d18786002adbf")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "8062010233:AAExAW3Z-kpT17OTUXg0GQkCVsc7qnDUbXQ")
    BOT_USERNAME = os.environ.get("BOT_USERNAME", "@Urluploader_z_bot")
    
    # Database
    DATABASE_URL = os.environ.get("DATABASE_URL", "mongodb+srv://moviedatabase:venura%408907@cluster0.hg0etvt.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
    
    # Logging
    LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", "-1002897456594"))
    
    # Owner
    OWNER_ID = int(os.environ.get("OWNER_ID", "8304706556"))
    
    # Session for user bot (if needed)
    SESSION_STR = os.environ.get("SESSION_STR", "")
    
    # Update channel
    UPDATE_CHANNEL = os.environ.get("UPDATE_CHANNEL", "https://t.me/zerodevbro")
    DEVELOPER = "@Zeroboy216"
    
    # Download/Upload settings
    MAX_FILE_SIZE = 4 * 1024 * 1024 * 1024  # 4 GB
    SPEED_LIMIT = 500 * 1024 * 1024  # 500 MB/s (SUPER FAST!)
    CHUNK_SIZE = 2 * 1024 * 1024  # 2 MB chunks for maximum speed
    
    # Download directory
    DOWNLOAD_DIR = "downloads"
    
    # Torrent settings
    TORRENT_DOWNLOAD_PATH = "downloads/torrents"
    TORRENT_SEED_TIME = 0  # Don't seed after download
    
    # Welcome message
    START_MESSAGE = """ʜᴇʏ {name}**, 
ɪ ᴀᴍ ᴛʜᴇ ᴍᴏsᴛ ᴘᴏᴡᴇʀғᴜʟ ᴀᴜᴛᴏ ᴜʀʟ ᴜᴘʟᴏᴀᴅᴇʀ ʙᴏᴛ ᴡɪᴛʜ ᴘʀᴇᴍɪᴜᴍ ғᴇᴀᴛᴜʀᴇs 🚀
ɪ ᴄᴀɴ ᴜᴘʟᴏᴀᴅ ᴍᴏᴠɪᴇs ᴀɴᴅ ᴍᴏʀᴇ — ᴊᴜsᴛ ᴘᴀsᴛᴇ ᴀ ᴜʀʟ ᴏʀ ᴀ ᴍᴀɢɴᴇᴛ/ᴛᴏʀʀᴇɴᴛ ✨"""

    HELP_MESSAGE = """
**Hᴏᴡ Tᴏ Usᴇ Tʜɪs Bᴏᴛ** 🤔
   
𖣔 Fɪʀsᴛ ɢᴏ ᴛᴏ ᴛʜᴇ /settings ᴀɴᴅ ᴄʜᴀɴɢᴇ ᴛʜᴇ ʙᴏᴛ ʙᴇʜᴀᴠɪᴏʀ ᴀs ʏᴏᴜʀ ᴄʜᴏɪᴄᴇ.

𖣔 Sᴇɴᴅ ᴍᴇ ᴛʜᴇ ᴄᴜsᴛᴏᴍ ᴛʜᴜᴍʙɴᴀɪʟ ᴛᴏ sᴀᴠᴇ ɪᴛ ᴘᴇʀᴍᴀɴᴇɴᴛʟʏ.

𖣔 **Sᴇɴᴅ ᴜʀʟ | Nᴇᴡ ɴᴀᴍᴇ.ᴍᴋᴠ**

𖣔 Sᴇʟᴇᴄᴛ ᴛʜᴇ ᴅᴇsɪʀᴇᴅ ᴏᴘᴛɪᴏɴ.

𖣔 Usᴇ `/caption` ᴛᴏ sᴇᴛ ᴄᴀᴘᴛɪᴏɴ ᴀs Rᴇᴘʟʏ ᴛᴏ ᴍᴇᴅɪᴀ

"""
    ABOUT_MESSAGE = """
╭───────────⍟
├📛 **Mʏ Nᴀᴍᴇ** : URL Uᴘʟᴏᴀᴅᴇʀ Bᴏᴛ
├📢 **Fʀᴀᴍᴇᴡᴏʀᴋ** : <a href=https://docs.pyrogram.org/>PʏʀᴏBʟᴀᴄᴋ 2.7.4</a>
├💮 **Lᴀɴɢᴜᴀɢᴇ** : <a href=https://www.python.org>Pʏᴛʜᴏɴ 3.13.7</a>
├💾 **Dᴀᴛᴀʙᴀsᴇ** : <a href=https://cloud.mongodb.com>MᴏɴɢᴏDB</a>
├🚨 **Sᴜᴘᴘᴏʀᴛ Gʀᴏᴜᴘ** : <a href=https://t.me/zerodevsupport> Zᴇʀᴏ Sᴜᴘᴘᴏʀᴛ</a>
├🥏 **Cʜᴀɴɴᴇʟ** : <a href=https://t.me/zerodevbro> Zᴇʀᴏ Dᴇᴠ </a>
├👨‍💻 **Cʀᴇᴀᴛᴇʀ** :  @Zeroboy216
╰───────────────⍟
"""
