import time
import asyncio
import math
from typing import Optional
from urllib.parse import urlparse

class Progress:
    """Progress tracker for downloads and uploads with stunning UI - Optimized"""
    
    def __init__(self, client, message):
        self.client = client
        self.message = message
        self.start_time = time.time()
        self.last_update = 0
        self.update_interval = 2.0  # Update every 2 seconds to reduce API calls
        self.last_percentage = -1  # Track last percentage to avoid duplicate updates
        
    async def progress_callback(self, current, total, status="Downloading"):
        """Progress callback with beautiful box-style formatting - Optimized"""
        now = time.time()
        
        # Calculate percentage early
        percentage = calculate_percentage(current, total)
        
        # Skip update if:
        # 1. Too soon since last update
        # 2. Percentage hasn't changed by at least 2%
        if (now - self.last_update < self.update_interval and 
            abs(percentage - self.last_percentage) < 2):
            return
            
        self.last_update = now
        self.last_percentage = percentage
        elapsed = now - self.start_time
        
        if current == 0 or elapsed == 0:
            return
        
        # Optimized calculations
        speed = current / elapsed
        speed_mb = speed / (1024 * 1024)
        eta_seconds = max(0, (total - current) / speed) if speed > 0 else 0
        
        # Format data efficiently
        current_mb = current / (1024 * 1024)
        total_mb = total / (1024 * 1024)
        
        # Create beautiful boxed progress bar (20 blocks for faster rendering)
        progress_bar = create_progress_bar(percentage, length=20)
        
        # Box borders
        top_border = "╭" + "─" * 32 + "╮"
        bottom_border = "╰" + "─" * 32 + "╯"
        
        # Status emoji and icon (optimized with dict lookup)
        status_config = get_status_config(status)
        
        # Speed indicator
        speed_indicator = get_speed_indicator(speed_mb)
        
        # Create stunning boxed progress message
        text = (
            f"{top_border}\n"
            f"│ {status_config['emoji']} **{status}**\n"
            f"│\n"
            f"│ [{progress_bar}] **{percentage:.1f}%**\n"
            f"│\n"
            f"│ 📦 **Size:** `{current_mb:.1f}` / `{total_mb:.1f} MB`\n"
            f"│ {status_config['icon']} **Speed:** `{speed_mb:.1f} MB/s` {speed_indicator}\n"
            f"│ ⏱️ **ETA:** `{format_time(eta_seconds)}`\n"
            f"│ ⏰ **Elapsed:** `{format_time(elapsed)}`\n"
            f"{bottom_border}"
        )
        
        try:
            await self.message.edit_text(text, disable_web_page_preview=True)
        except Exception:
            # Silently ignore edit errors (message too old, same content, etc.)
            pass

def get_status_config(status):
    """Get status configuration - Optimized with dict"""
    status_lower = status.lower()
    
    configs = {
        'download': {'emoji': '📥', 'icon': '⬇️'},
        'upload': {'emoji': '📤', 'icon': '⬆️'},
        'torrent': {'emoji': '🌊', 'icon': '🔄'},
    }
    
    for key, config in configs.items():
        if key in status_lower:
            return config
    
    return {'emoji': '⚙️', 'icon': '⚡'}

def get_speed_indicator(speed_mb):
    """Get visual speed indicator based on speed - Optimized"""
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
    """Format seconds to human readable time - Optimized"""
    if seconds <= 0 or math.isnan(seconds) or math.isinf(seconds):
        return "0s"
    
    seconds = int(seconds)
    
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"

def humanbytes(size):
    """Convert bytes to human readable format - Optimized"""
    if not size or size <= 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    power = 1024
    n = 0
    
    while size >= power and n < len(units) - 1:
        size /= power
        n += 1
    
    # Use 1 decimal for smaller precision, faster formatting
    return f"{size:.1f} {units[n]}"

async def speed_limiter(chunk_size, speed_limit):
    """Limit download/upload speed - Optimized"""
    if speed_limit <= 0:
        return
    
    delay = chunk_size / speed_limit
    if delay > 0.001:  # Only sleep if delay is meaningful
        await asyncio.sleep(delay)

def is_url(text):
    """Check if text is a valid URL - Optimized"""
    if not text or not isinstance(text, str):
        return False
    
    text_lower = text.lower().strip()
    
    # Quick check for common URL schemes
    return (text_lower.startswith(('http://', 'https://', 'ftp://', 'ftps://')) or 
            text_lower.startswith('www.'))

def is_magnet(text):
    """Check if text is a magnet link - Optimized"""
    if not text or not isinstance(text, str):
        return False
    return text.lower().strip().startswith('magnet:?')

# Precompile translation table for faster sanitization
_INVALID_CHARS_TABLE = str.maketrans('<>:"/\\|?*', '_________')

def sanitize_filename(filename):
    """Remove invalid characters from filename - Highly optimized"""
    if not filename or not isinstance(filename, str):
        return "file"
    
    # Use translation table for fast character replacement
    filename = filename.translate(_INVALID_CHARS_TABLE)
    
    # Remove control characters (ASCII 0-31) - optimized
    filename = ''.join(c for c in filename if ord(c) > 31)
    
    # Replace multiple spaces/underscores - optimized
    while '  ' in filename:
        filename = filename.replace('  ', ' ')
    while '__' in filename:
        filename = filename.replace('__', '_')
    
    # Strip and check
    filename = filename.strip('. _')
    
    if not filename:
        return "file"
    
    # Limit filename length
    if len(filename) > 255:
        name, ext = split_filename_ext(filename)
        max_name_len = 255 - len(ext) - 1 if ext else 255
        filename = f"{name[:max_name_len]}.{ext}" if ext else name[:255]
    
    return filename

def split_filename_ext(filename):
    """Split filename into name and extension - Optimized"""
    if '.' not in filename:
        return filename, ''
    
    parts = filename.rsplit('.', 1)
    return parts[0], parts[1]

def get_file_extension(filename):
    """Get file extension from filename - Optimized"""
    if not filename or not isinstance(filename, str):
        return ''
    
    if '.' not in filename:
        return ''
    
    return filename.rsplit('.', 1)[-1].lower()

# Pre-define sets for faster lookup
_VIDEO_EXTENSIONS = {
    'mp4', 'mkv', 'avi', 'mov', 'flv', 'wmv', 
    'webm', 'm4v', 'mpg', 'mpeg', '3gp', 'ts',
    'vob', 'ogv', 'gifv', 'mng', 'qt', 'yuv',
    'rm', 'rmvb', 'asf', 'm2ts', 'mts'
}

_AUDIO_EXTENSIONS = {
    'mp3', 'wav', 'flac', 'aac', 'ogg', 
    'wma', 'm4a', 'opus', 'ape', 'alac',
    'aiff', 'dsd', 'pcm', 'amr', 'awb'
}

_DOCUMENT_EXTENSIONS = {
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 
    'ppt', 'pptx', 'txt', 'zip', 'rar', '7z',
    'tar', 'gz', 'bz2', 'epub', 'mobi',
    'azw', 'azw3', 'djvu', 'cbr', 'cbz'
}

def is_video_file(filename):
    """Check if file is a video - Optimized with set lookup"""
    return get_file_extension(filename) in _VIDEO_EXTENSIONS

def is_audio_file(filename):
    """Check if file is an audio file - Optimized"""
    return get_file_extension(filename) in _AUDIO_EXTENSIONS

def is_document_file(filename):
    """Check if file is a document - Optimized"""
    return get_file_extension(filename) in _DOCUMENT_EXTENSIONS

def format_duration(seconds):
    """Format duration in seconds to HH:MM:SS - Optimized"""
    if not seconds or seconds < 0:
        return "00:00"
    
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d}" if hours > 0 else f"{minutes:02d}:{secs:02d}"

async def run_command(command):
    """Run shell command asynchronously - Optimized with timeout"""
    try:
        process = await asyncio.wait_for(
            asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            ),
            timeout=300  # 5 minute timeout
        )
        
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=300
        )
        
        return (
            process.returncode,
            stdout.decode('utf-8', errors='ignore'),
            stderr.decode('utf-8', errors='ignore')
        )
    except asyncio.TimeoutError:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)

def truncate_text(text, max_length=100):
    """Truncate text to max length - Optimized"""
    if not text or not isinstance(text, str):
        return ""
    
    return text if len(text) <= max_length else f"{text[:max_length - 3]}..."

def create_progress_bar(percentage, length=20):
    """Create a beautiful progress bar string - Optimized"""
    percentage = max(0, min(100, percentage))
    filled = int((percentage / 100) * length)
    
    if filled == length:
        return "█" * length
    elif filled > 0:
        empty = length - filled
        return "█" * filled + "▒" * empty
    else:
        return "░" * length

def parse_torrent_info(info_dict):
    """Parse torrent info dictionary - Optimized"""
    if not info_dict:
        return {
            'name': 'Unknown',
            'size': 0,
            'files': 1,
            'pieces': 0
        }
    
    return {
        'name': info_dict.get('name', 'Unknown'),
        'size': info_dict.get('total_size', 0),
        'files': info_dict.get('num_files', 1),
        'pieces': info_dict.get('num_pieces', 0)
    }

def validate_url(url):
    """Validate if URL is properly formatted - Optimized"""
    if not url or not isinstance(url, str):
        return False
    
    try:
        result = urlparse(url.strip())
        return bool(result.scheme and result.netloc)
    except Exception:
        return False

def get_readable_message(current, total, status="Processing"):
    """Get a readable progress message - Optimized"""
    if total <= 0:
        return f"{status}: Calculating..."
    
    percentage = calculate_percentage(current, total)
    current_readable = humanbytes(current)
    total_readable = humanbytes(total)
    
    return f"{status}: {percentage:.1f}% ({current_readable}/{total_readable})"

def estimate_completion_time(current, total, start_time):
    """Estimate completion time based on current progress - Optimized"""
    if current <= 0 or total <= 0:
        return "Calculating..."
    
    elapsed = time.time() - start_time
    
    if elapsed <= 0:
        return "Calculating..."
    
    remaining = total - current
    rate = current / elapsed
    
    if rate <= 0:
        return "Calculating..."
    
    return format_time(remaining / rate)

def get_file_size_mb(size_bytes):
    """Convert bytes to MB - Inline optimized"""
    return size_bytes / (1024 * 1024)

def calculate_percentage(current, total):
    """Safely calculate percentage - Optimized"""
    if total <= 0:
        return 0.0
    return min(100.0, (current * 100.0) / total)

def format_speed(bytes_per_second):
    """Format speed in human readable format - Optimized"""
    if bytes_per_second < 1024:
        return f"{bytes_per_second:.0f} B/s"
    
    speed_kb = bytes_per_second / 1024
    if speed_kb < 1024:
        return f"{speed_kb:.1f} KB/s"
    
    speed_mb = speed_kb / 1024
    if speed_mb < 1024:
        return f"{speed_mb:.1f} MB/s"
    
    speed_gb = speed_mb / 1024
    return f"{speed_gb:.2f} GB/s"

# Additional utility functions

def get_mime_type(filename):
    """Get MIME type from filename - Fast"""
    ext = get_file_extension(filename)
    
    # Common MIME types for quick lookup
    mime_types = {
        # Video
        'mp4': 'video/mp4',
        'mkv': 'video/x-matroska',
        'avi': 'video/x-msvideo',
        'mov': 'video/quicktime',
        'webm': 'video/webm',
        # Audio
        'mp3': 'audio/mpeg',
        'wav': 'audio/wav',
        'flac': 'audio/flac',
        'ogg': 'audio/ogg',
        'm4a': 'audio/mp4',
        # Documents
        'pdf': 'application/pdf',
        'zip': 'application/zip',
        'rar': 'application/x-rar-compressed',
        '7z': 'application/x-7z-compressed',
        'txt': 'text/plain',
    }
    
    return mime_types.get(ext, 'application/octet-stream')

def format_file_info(filepath, file_size):
    """Format file information for display - Optimized"""
    filename = filepath.split('/')[-1] if '/' in filepath else filepath
    size_readable = humanbytes(file_size)
    extension = get_file_extension(filename)
    
    file_type = "Unknown"
    if is_video_file(filename):
        file_type = "Video"
    elif is_audio_file(filename):
        file_type = "Audio"
    elif is_document_file(filename):
        file_type = "Document"
    
    return {
        'name': filename,
        'size': size_readable,
        'type': file_type,
        'extension': extension.upper()
    }

def cleanup_temp_files(directory, pattern="*.tmp"):
    """Cleanup temporary files - Async safe"""
    import glob
    import os
    
    try:
        temp_files = glob.glob(os.path.join(directory, pattern))
        for temp_file in temp_files:
            try:
                os.remove(temp_file)
            except Exception:
                pass
        return len(temp_files)
    except Exception:
        return 0
