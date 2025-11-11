import time
import asyncio
import math
from typing import Optional

class Progress:
    """Progress tracker for downloads and uploads with stunning UI"""
    
    def __init__(self, client, message):
        self.client = client
        self.message = message
        self.start_time = time.time()
        self.last_update = 0
        self.update_interval = 1.5  # Update every 1.5 seconds for smoother updates
        
    async def progress_callback(self, current, total, status="Downloading"):
        """Progress callback with beautiful box-style formatting"""
        now = time.time()
        
        # Update only every N seconds to avoid flood
        if now - self.last_update < self.update_interval:
            return
            
        self.last_update = now
        elapsed = now - self.start_time
        
        if current == 0 or elapsed == 0:
            return
            
        speed = current / elapsed
        percentage = (current * 100 / total) if total > 0 else 0
        eta_seconds = (total - current) / speed if speed > 0 else 0
        
        # Format data
        current_mb = current / (1024 * 1024)
        total_mb = total / (1024 * 1024)
        speed_mb = speed / (1024 * 1024)
        
        # Create beautiful boxed progress bar (25 blocks for precision)
        bar_length = 25
        filled = int((percentage / 100) * bar_length)
        empty = bar_length - filled
        
        # Use block characters for smooth gradient effect
        if filled == bar_length:
            progress_bar = "█" * bar_length
        elif filled > 0:
            progress_bar = "█" * filled + "▒" * empty
        else:
            progress_bar = "░" * bar_length
        
        # Box borders and styling
        top_border = "╭" + "─" * 32 + "╮"
        bottom_border = "╰" + "─" * 32 + "╯"
        
        # Status emoji and color indicator
        if "Download" in status:
            status_emoji = "📥"
            status_icon = "⬇️"
        elif "Upload" in status:
            status_emoji = "📤"
            status_icon = "⬆️"
        elif "Torrent" in status:
            status_emoji = "🌊"
            status_icon = "🔄"
        else:
            status_emoji = "⚙️"
            status_icon = "⚡"
        
        # Speed indicator bars
        speed_bars = get_speed_indicator(speed_mb)
        
        # Create stunning boxed progress message
        text = (
            f"{top_border}\n"
            f"│ {status_emoji} **{status}**\n"
            f"│\n"
            f"│ [{progress_bar}] **{percentage:.1f}%**\n"
            f"│\n"
            f"│ 📦 **Size:** `{current_mb:.2f}` / `{total_mb:.2f} MB`\n"
            f"│ {status_icon} **Speed:** `{speed_mb:.2f} MB/s` {speed_bars}\n"
            f"│ ⏱️ **ETA:** `{format_time(eta_seconds)}`\n"
            f"│ ⏰ **Elapsed:** `{format_time(elapsed)}`\n"
            f"{bottom_border}"
        )
        
        try:
            await self.message.edit_text(text)
        except Exception:
            pass

def get_speed_indicator(speed_mb):
    """Get visual speed indicator based on speed"""
    if speed_mb < 1:
        return "🐌"
    elif speed_mb < 5:
        return "🚶"
    elif speed_mb < 10:
        return "🏃"
    elif speed_mb < 20:
        return "🚗"
    elif speed_mb < 50:
        return "✈️"
    else:
        return "🚀"

def format_time(seconds):
    """Format seconds to human readable time"""
    if seconds < 0 or math.isnan(seconds) or math.isinf(seconds):
        return "0s"
    
    seconds = int(seconds)
    
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}m {secs}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"

def humanbytes(size):
    """Convert bytes to human readable format"""
    if not size or size < 0:
        return "0 B"
    
    power = 1024
    n = 0
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    
    while size >= power and n < len(units) - 1:
        size /= power
        n += 1
    
    return f"{size:.2f} {units[n]}"

async def speed_limiter(chunk_size, speed_limit):
    """Limit download/upload speed"""
    if speed_limit <= 0:
        return
    
    delay = chunk_size / speed_limit
    await asyncio.sleep(delay)

def is_url(text):
    """Check if text is a valid URL"""
    if not text or not isinstance(text, str):
        return False
    
    url_indicators = [
        'http://', 'https://', 'www.',
        'ftp://', 'ftps://'
    ]
    
    text_lower = text.lower().strip()
    return any(text_lower.startswith(indicator) for indicator in url_indicators)

def is_magnet(text):
    """Check if text is a magnet link"""
    if not text or not isinstance(text, str):
        return False
    return text.lower().strip().startswith('magnet:?')

def sanitize_filename(filename):
    """Remove invalid characters from filename with better handling"""
    if not filename or not isinstance(filename, str):
        return "file"
    
    # Invalid characters for filenames (Windows + Linux)
    invalid_chars = '<>:"/\\|?*\x00'
    
    # Replace invalid characters with underscore
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove control characters (ASCII 0-31)
    filename = ''.join(char for char in filename if ord(char) > 31)
    
    # Replace multiple spaces/underscores with single one
    while '  ' in filename:
        filename = filename.replace('  ', ' ')
    while '__' in filename:
        filename = filename.replace('__', '_')
    
    # Remove leading/trailing spaces, dots, and underscores
    filename = filename.strip('. _')
    
    # If filename is empty after sanitization
    if not filename:
        filename = "file"
    
    # Limit filename length (255 chars for most filesystems)
    if len(filename) > 255:
        name, ext = split_filename_ext(filename)
        max_name_len = 255 - len(ext) - 1
        filename = name[:max_name_len] + '.' + ext if ext else name[:255]
    
    return filename

def split_filename_ext(filename):
    """Split filename into name and extension"""
    if '.' in filename:
        parts = filename.rsplit('.', 1)
        return parts[0], parts[1]
    return filename, ''

def get_file_extension(filename):
    """Get file extension from filename"""
    if not filename or not isinstance(filename, str) or '.' not in filename:
        return ''
    return filename.rsplit('.', 1)[-1].lower()

def is_video_file(filename):
    """Check if file is a video based on extension"""
    video_extensions = [
        'mp4', 'mkv', 'avi', 'mov', 'flv', 'wmv', 
        'webm', 'm4v', 'mpg', 'mpeg', '3gp', 'ts',
        'vob', 'ogv', 'gifv', 'mng', 'qt', 'yuv',
        'rm', 'rmvb', 'asf', 'm2ts', 'mts'
    ]
    
    ext = get_file_extension(filename)
    return ext in video_extensions

def is_audio_file(filename):
    """Check if file is an audio file"""
    audio_extensions = [
        'mp3', 'wav', 'flac', 'aac', 'ogg', 
        'wma', 'm4a', 'opus', 'ape', 'alac',
        'aiff', 'dsd', 'pcm', 'amr', 'awb'
    ]
    
    ext = get_file_extension(filename)
    return ext in audio_extensions

def is_document_file(filename):
    """Check if file is a document"""
    doc_extensions = [
        'pdf', 'doc', 'docx', 'xls', 'xlsx', 
        'ppt', 'pptx', 'txt', 'zip', 'rar', '7z',
        'tar', 'gz', 'bz2', 'epub', 'mobi',
        'azw', 'azw3', 'djvu', 'cbr', 'cbz'
    ]
    
    ext = get_file_extension(filename)
    return ext in doc_extensions

def format_duration(seconds):
    """Format duration in seconds to HH:MM:SS"""
    if not seconds or seconds < 0:
        return "00:00"
    
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"

async def run_command(command):
    """Run shell command asynchronously"""
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        return process.returncode, stdout.decode('utf-8', errors='ignore'), stderr.decode('utf-8', errors='ignore')
    except Exception as e:
        return -1, "", str(e)

def truncate_text(text, max_length=100):
    """Truncate text to max length"""
    if not text or not isinstance(text, str):
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length - 3] + "..."

def create_progress_bar(percentage, length=25):
    """Create a beautiful progress bar string"""
    if percentage < 0:
        percentage = 0
    elif percentage > 100:
        percentage = 100
    
    filled = int((percentage / 100) * length)
    empty = length - filled
    
    if filled == length:
        return "█" * length
    elif filled > 0:
        return "█" * filled + "▒" * empty
    else:
        return "░" * length

def parse_torrent_info(info_dict):
    """Parse torrent info dictionary"""
    if not info_dict:
        return {}
    
    return {
        'name': info_dict.get('name', 'Unknown'),
        'size': info_dict.get('total_size', 0),
        'files': info_dict.get('num_files', 1),
        'pieces': info_dict.get('num_pieces', 0)
    }

def validate_url(url):
    """Validate if URL is properly formatted"""
    if not url or not isinstance(url, str):
        return False
    
    # Basic URL validation
    try:
        from urllib.parse import urlparse
        result = urlparse(url.strip())
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def get_readable_message(current, total, status="Processing"):
    """Get a readable progress message"""
    if total <= 0:
        return f"{status}: Calculating..."
    
    percentage = (current / total) * 100
    current_readable = humanbytes(current)
    total_readable = humanbytes(total)
    
    return f"{status}: {percentage:.1f}% ({current_readable}/{total_readable})"

def estimate_completion_time(current, total, start_time):
    """Estimate completion time based on current progress"""
    if current <= 0 or total <= 0:
        return "Calculating..."
    
    elapsed = time.time() - start_time
    
    if elapsed <= 0:
        return "Calculating..."
    
    rate = current / elapsed
    remaining = total - current
    
    if rate <= 0:
        return "Calculating..."
    
    eta = remaining / rate
    
    return format_time(eta)

def get_file_size_mb(size_bytes):
    """Convert bytes to MB"""
    return size_bytes / (1024 * 1024)

def calculate_percentage(current, total):
    """Safely calculate percentage"""
    if total <= 0:
        return 0.0
    return min(100.0, (current / total) * 100)

def format_speed(bytes_per_second):
    """Format speed in human readable format"""
    speed_mb = bytes_per_second / (1024 * 1024)
    
    if speed_mb < 1:
        speed_kb = bytes_per_second / 1024
        return f"{speed_kb:.2f} KB/s"
    elif speed_mb < 1024:
        return f"{speed_mb:.2f} MB/s"
    else:
        speed_gb = speed_mb / 1024
        return f"{speed_gb:.2f} GB/s"
