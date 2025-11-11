# 🔗 Telegram URL Uploader Bot

<div align="center">

<img src="https://github.com/user-attachments/assets/d11e637d-b3da-42d6-9346-fe399665ca5c" alt="Telegram URL Uploader Bot" width="100%"/>

[![Python](https://img.shields.io/badge/Python-3.13.7-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Pyrogram](https://img.shields.io/badge/Pyrogram-2.7.4-3776AB?style=for-the-badge&logo=telegram&logoColor=white)](https://docs.pyrogram.org/)
[![MongoDB](https://img.shields.io/badge/MongoDB-Cloud-47A248?style=for-the-badge&logo=mongodb&logoColor=white)](https://www.mongodb.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

**A powerful Telegram bot that can download files from any URL and upload them to Telegram with lightning speed!** ⚡

[![Demo Bot](https://img.shields.io/badge/🤖_Try_Demo_Bot-blue?style=for-the-badge)](https://t.me/Urluploader_z_bot)
[![Updates Channel](https://img.shields.io/badge/📢_Updates_Channel-blue?style=for-the-badge)](https://t.me/zerodevbro)
[![Report Bug](https://img.shields.io/badge/🐛_Report_Bug-red?style=for-the-badge)](https://github.com/zero-creation690/Url-uploader/issues)
[![Request Feature](https://img.shields.io/badge/💡_Feature_Request-green?style=for-the-badge)](https://github.com/zero-creation690/Url-uploader/issues)

</div>

---

## ✨ Features

### 🎯 Core Features

- **📥 Multi-Source Downloads**: HTTP/HTTPS, YouTube, Instagram, TikTok, Facebook, Twitter
- **🧲 Torrent Support**: Magnet links & .torrent files
- **🚀 Blazing Fast**: 500 MB/s download speed
- **💾 Large Files**: Support up to 4GB files
- **🎬 Original Quality**: No compression, preserve original resolution & audio

### 🛠️ Advanced Features

- **📊 Real-time Progress**: Live progress bar with speed and ETA
- **🎨 Custom Thumbnails**: Set permanent custom thumbnails
- **✏️ Smart Renaming**: Custom filenames with pattern support
- **📝 Custom Captions**: Dynamic caption templates
- **⚙️ User Settings**: Personalized bot behavior per user
- **📈 Statistics**: Detailed user and bot analytics

---

## 🔗 Supported Platforms

| Platform | Status | Features |
|----------|--------|----------|
| YouTube | ✅ | 4K, Playlists, Subtitles |
| Instagram | ✅ | Posts, Reels, Stories |
| TikTok | ✅ | Videos, Watermark-free |
| Facebook | ✅ | Videos, Reels |
| Twitter/X | ✅ | Videos, GIFs |
| Vimeo | ✅ | HD Videos |
| Direct Links | ✅ | Resume support |
| Torrents | ✅ | Magnet & .torrent |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.13.7 or higher
- Telegram Bot Token (Get from [@BotFather](https://t.me/BotFather))
- MongoDB Database (Free from [MongoDB Atlas](https://www.mongodb.com/cloud/atlas))

### Installation

#### 1. Clone the Repository

```bash
git clone https://github.com/zero-creation690/Url-uploader.git
cd Url-uploader
```

#### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

#### 4. Run the Bot

```bash
python bot.py
```

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with:

```env
# Telegram API (Required)
APP_ID=your_app_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token

# Database (Required)
DATABASE_URL=mongodb+srv://username:password@cluster.mongodb.net/

# Optional Settings
LOG_CHANNEL=-1001234567890
OWNER_ID=your_owner_id
SESSION_STR=your_session_string
```

### Get Telegram API Credentials

1. Go to [my.telegram.org](https://my.telegram.org)
2. Create application to get `APP_ID` and `API_HASH`
3. Create bot with [@BotFather](https://t.me/BotFather) to get `BOT_TOKEN`

---

## 📖 Usage

### Basic Commands

| Command | Description |
|---------|-------------|
| `/start` | Start the bot and show welcome |
| `/help` | Detailed help with usage guide |
| `/about` | Bot information and specifications |
| `/settings` | Configure bot behavior |
| `/status` | Your download statistics |
| `/rename` | Rename downloaded files |

### How to Use 🤔

1. **Configure Settings**
   ```
   First go to /settings and change the bot behavior as your choice
   ```

2. **Set Custom Thumbnail**
   ```
   Send me the custom thumbnail to save it permanently
   ```

3. **Download Files**
   ```
   Send url | New name.mkv
   ```

4. **Set Captions**
   ```
   Use /caption to set caption as Reply to media
   ```

### Examples

**Download YouTube Video:**
```
https://youtube.com/watch?v=VIDEO_ID | MyVideo.mp4
```

**Download with Custom Name:**
```
https://example.com/file.zip | CustomName.zip
```

**Set Permanent Thumbnail:**
Just send any image to the bot

---

## 🏗️ Project Structure

```
Url-uploader/
├── bot.py                 # Main bot handler
├── config.py             # Configuration manager
├── database.py           # MongoDB operations
├── downloader.py         # Multi-source downloader
├── helpers.py            # Utility functions
├── requirements.txt      # Dependencies
└── .env                 # Environment variables
```

### Technical Architecture

- **Framework**: PyroBlack 2.7.4
- **Language**: Python 3.13.7
- **Database**: MongoDB Cloud
- **HTTP Client**: aiohttp
- **Video Processing**: yt-dlp, FFmpeg
- **Torrent**: libtorrent

---

## 🚀 Deployment

### Local Deployment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Run the bot
python bot.py
```

### Docker Deployment

```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "bot.py"]
```

### VPS Deployment

```bash
# Using screen to keep bot running
screen -S url-bot
python bot.py
# Ctrl+A then D to detach
```

---

## 📊 API Reference

### Supported URL Formats

```python
# Direct URLs
"https://example.com/file.mp4"

# YouTube
"https://youtube.com/watch?v=..."
"https://youtu.be/..."

# Instagram
"https://instagram.com/p/..."
"https://www.instagram.com/reel/..."

# TikTok
"https://tiktok.com/@user/video/..."

# Torrent
"magnet:?xt=urn:btih:..."
"*.torrent files"
```

---

## 🤝 Contributing

We love contributions! Here's how to help:

1. **Fork the Repository**
2. **Create a Feature Branch**
   ```bash
   git checkout -b feature/AmazingFeature
   ```
3. **Commit Your Changes**
   ```bash
   git commit -m 'Add some AmazingFeature'
   ```
4. **Push to the Branch**
   ```bash
   git push origin feature/AmazingFeature
   ```
5. **Open a Pull Request**

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest

# Code formatting
black .
```

---

## 🐛 Troubleshooting

### Common Issues

**Bot not starting:**
- Check API credentials in `.env`
- Verify MongoDB connection string
- Ensure Python version is 3.13.7+

**Downloads failing:**
- Check internet connection
- Verify URL is accessible
- Some sites may block bot requests

**Uploads failing:**
- File size exceeds 4GB Telegram limit
- Check available disk space
- Verify Telegram API limits

### Getting Help

- 📢 **Updates Channel**: [@zerodevbro](https://t.me/zerodevbro)
- 💬 **Support Group**: [@zerodevbro](https://t.me/zerodevbro)
- 👨‍💻 **Developer**: [@Zeroboy216](https://t.me/Zeroboy216)
- 🐛 **Issues**: [GitHub Issues](https://github.com/zero-creation690/Url-uploader/issues)

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [Pyrogram Team](https://github.com/pyrogram/pyrogram) - Amazing Telegram MTProto framework
- [yt-dlp Developers](https://github.com/yt-dlp/yt-dlp) - Robust video downloader
- [MongoDB](https://www.mongodb.com/) - Reliable cloud database
- [Telegram](https://telegram.org/) - Platform for innovation

---

## 📞 Support

If you need help or want to suggest features:

- 🤖 **Demo Bot**: [@Urluploader_z_bot](https://t.me/Urluploader_z_bot)
- 💬 **Support Group**: [@zerodevbro](https://t.me/zerodevbro)
- 📢 **Updates Channel**: [@zerodevbro](https://t.me/zerodevbro)
- 👨‍💻 **Developer**: [@Zeroboy216](https://t.me/Zeroboy216)
- 🐛 **Issues**: [GitHub Issues](https://github.com/zero-creation690/Url-uploader/issues)
- 💾 **Repository**: [zero-creation690/Url-uploader](https://github.com/zero-creation690/Url-uploader)

---

<div align="center">

### ⭐ Don't forget to star this repository if you find it useful!

**Made with ❤️ by [Zero Boy](https://github.com/zero-creation690)**

[![Try Demo Bot](https://img.shields.io/badge/🤖_Try_Demo_Bot-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/Urluploader_z_bot)
[![Join Channel](https://img.shields.io/badge/📢_Join_Channel-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/zerodevbro)
[![GitHub](https://img.shields.io/badge/💻_GitHub-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/zero-creation690/Url-uploader)

</div>
