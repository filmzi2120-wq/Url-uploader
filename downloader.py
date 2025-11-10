import os
import aiohttp
import asyncio
import yt_dlp
from config import Config
from helpers import speed_limiter, sanitize_filename
import time

class Downloader:
    def __init__(self):
        self.download_dir = Config.DOWNLOAD_DIR
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
    
    async def download_file(self, url, filename=None, progress_callback=None):
        """Download file from URL using aiohttp with speed limit"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return None, f"Failed to download: HTTP {response.status}"
                    
                    total_size = int(response.headers.get('content-length', 0))
                    
                    if total_size > Config.MAX_FILE_SIZE:
                        return None, "File size exceeds 4GB limit"
                    
                    # Get filename from headers or use provided
                    if not filename:
                        content_disp = response.headers.get('content-disposition', '')
                        if 'filename=' in content_disp:
                            filename = content_disp.split('filename=')[1].strip('"')
                        else:
                            filename = url.split('/')[-1].split('?')[0] or 'downloaded_file'
                    
                    filename = sanitize_filename(filename)
                    filepath = os.path.join(self.download_dir, filename)
                    
                    downloaded = 0
                    start_time = time.time()
                    
                    with open(filepath, 'wb') as f:
                        async for chunk in response.content.iter_chunked(Config.CHUNK_SIZE):
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            # Speed limiting
                            elapsed = time.time() - start_time
                            expected_time = downloaded / Config.SPEED_LIMIT
                            if elapsed < expected_time:
                                await asyncio.sleep(expected_time - elapsed)
                            
                            # Progress callback
                            if progress_callback:
                                await progress_callback(downloaded, total_size, "Downloading")
                    
                    return filepath, None
                    
        except Exception as e:
            return None, f"Download error: {str(e)}"
    
    async def download_ytdlp(self, url, progress_callback=None):
        """Download using yt-dlp (for YouTube, Instagram, etc.)"""
        try:
            ydl_opts = {
                'outtmpl': os.path.join(self.download_dir, '%(title)s.%(ext)s'),
                'format': 'best',
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }
            
            # Download in a thread to avoid blocking
            loop = asyncio.get_event_loop()
            
            def download():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    filename = ydl.prepare_filename(info)
                    return filename, info.get('title', 'Video')
            
            filepath, title = await loop.run_in_executor(None, download)
            
            if os.path.exists(filepath):
                return filepath, None
            else:
                return None, "Failed to download video"
                
        except Exception as e:
            return None, f"yt-dlp error: {str(e)}"
    
    async def download(self, url, filename=None, progress_callback=None):
        """Main download function - chooses appropriate method"""
        # Check if URL is for YouTube, Instagram, etc.
        video_domains = ['youtube.com', 'youtu.be', 'instagram.com', 'facebook.com', 
                        'twitter.com', 'tiktok.com', 'vimeo.com']
        
        is_video_url = any(domain in url.lower() for domain in video_domains)
        
        if is_video_url:
            return await self.download_ytdlp(url, progress_callback)
        else:
            return await self.download_file(url, filename, progress_callback)
    
    def cleanup(self, filepath):
        """Remove downloaded file"""
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception:
            pass

downloader = Downloader()
