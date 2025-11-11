import os
import aiohttp
import asyncio
import yt_dlp
import libtorrent as lt
import subprocess
from config import Config
from helpers import speed_limiter, sanitize_filename, is_video_file
import time
import shutil

class Downloader:
    def __init__(self):
        self.download_dir = Config.DOWNLOAD_DIR
        self.torrent_dir = Config.TORRENT_DOWNLOAD_PATH
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
        if not os.path.exists(self.torrent_dir):
            os.makedirs(self.torrent_dir)
    
    async def download_file(self, url, filename=None, progress_callback=None):
        """Download file from URL using aiohttp with 200 MB/s speed - preserves original quality"""
        try:
            timeout = aiohttp.ClientTimeout(total=None, connect=60)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': '*/*',
                'Accept-Encoding': 'identity',  # Don't compress, keep original
                'Connection': 'keep-alive'
            }
            
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                async with session.get(url, allow_redirects=True) as response:
                    if response.status != 200:
                        return None, f"Failed to download: HTTP {response.status}"
                    
                    total_size = int(response.headers.get('content-length', 0))
                    
                    if total_size > Config.MAX_FILE_SIZE:
                        return None, "File size exceeds 4GB limit"
                    
                    # Get filename from headers or use provided
                    if not filename:
                        content_disp = response.headers.get('content-disposition', '')
                        if 'filename=' in content_disp:
                            filename = content_disp.split('filename=')[1].strip('"\'')
                        else:
                            filename = url.split('/')[-1].split('?')[0] or 'downloaded_file'
                    
                    filename = sanitize_filename(filename)
                    filepath = os.path.join(self.download_dir, filename)
                    
                    downloaded = 0
                    start_time = time.time()
                    last_update = 0
                    
                    # Write in binary mode to preserve original file
                    with open(filepath, 'wb') as f:
                        async for chunk in response.content.iter_chunked(Config.CHUNK_SIZE):
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            # Progress callback every 2 seconds
                            current_time = time.time()
                            if progress_callback and (current_time - last_update) >= 2:
                                last_update = current_time
                                await progress_callback(downloaded, total_size, "Downloading")
                            
                            # Minimal delay for 200 MB/s speed
                            await asyncio.sleep(0.001)
                    
                    return filepath, None
                    
        except Exception as e:
            return None, f"Download error: {str(e)}"
    
    async def download_ytdlp(self, url, progress_callback=None):
        """Download using yt-dlp with best quality and original audio"""
        try:
            ydl_opts = {
                'outtmpl': os.path.join(self.download_dir, '%(title)s.%(ext)s'),
                # Best video + best audio, preserve original quality
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best',
                'merge_output_format': 'mp4',
                'quiet': False,
                'no_warnings': False,
                'extract_flat': False,
                'writethumbnail': True,
                # Audio settings - keep original
                'postprocessor_args': [
                    '-c:v', 'copy',  # Copy video stream without re-encoding
                    '-c:a', 'aac',   # Use AAC for audio (best compatibility)
                    '-b:a', '320k',  # High quality audio bitrate
                    '-ar', '48000',  # 48kHz sample rate
                    '-ac', '2',      # Stereo audio
                ],
                'keepvideo': False,
                'prefer_ffmpeg': True,
                'postprocessors': [
                    {
                        'key': 'FFmpegVideoConvertor',
                        'preferedformat': 'mp4',
                    },
                    {
                        'key': 'FFmpegMetadata',
                        'add_metadata': True,
                    },
                    {
                        'key': 'EmbedThumbnail',
                        'already_have_thumbnail': False,
                    },
                ],
            }
            
            loop = asyncio.get_event_loop()
            
            def download():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    filename = ydl.prepare_filename(info)
                    # Get actual output file
                    base = os.path.splitext(filename)[0]
                    if os.path.exists(f"{base}.mp4"):
                        filename = f"{base}.mp4"
                    return filename, info.get('title', 'Video')
            
            filepath, title = await loop.run_in_executor(None, download)
            
            if os.path.exists(filepath):
                return filepath, None
            else:
                return None, "Failed to download video"
                
        except Exception as e:
            return None, f"yt-dlp error: {str(e)}"
    
    async def download_torrent(self, magnet_or_file, progress_callback=None):
        """Download torrent using libtorrent"""
        try:
            ses = lt.session()
            ses.listen_on(6881, 6891)
            
            params = {
                'save_path': self.torrent_dir,
                'storage_mode': lt.storage_mode_t.storage_mode_sparse,
            }
            
            # Check if it's a magnet link or file
            if magnet_or_file.startswith('magnet:'):
                handle = lt.add_magnet_uri(ses, magnet_or_file, params)
            else:
                # It's a torrent file path
                info = lt.torrent_info(magnet_or_file)
                handle = ses.add_torrent({'ti': info, 'save_path': self.torrent_dir})
            
            # Wait for metadata
            while not handle.has_metadata():
                await asyncio.sleep(1)
            
            info = handle.get_torrent_info()
            name = info.name()
            
            # Download
            while not handle.is_seed():
                s = handle.status()
                
                progress = s.progress * 100
                download_rate = s.download_rate / 1024 / 1024  # MB/s
                
                if progress_callback:
                    await progress_callback(
                        int(s.total_done),
                        int(s.total_wanted),
                        f"Torrenting ({download_rate:.2f} MB/s)"
                    )
                
                await asyncio.sleep(2)
            
            # Get downloaded file path
            filepath = os.path.join(self.torrent_dir, name)
            
            # Stop seeding
            ses.remove_torrent(handle)
            
            return filepath, None
            
        except Exception as e:
            return None, f"Torrent error: {str(e)}"
    
    async def download(self, url_or_file, filename=None, progress_callback=None):
        """Main download function - auto-detects type"""
        
        # Check if it's a magnet link
        if isinstance(url_or_file, str) and url_or_file.startswith('magnet:'):
            return await self.download_torrent(url_or_file, progress_callback)
        
        # Check if it's a torrent file
        if isinstance(url_or_file, str) and url_or_file.endswith('.torrent'):
            return await self.download_torrent(url_or_file, progress_callback)
        
        # Check if URL is for YouTube, Instagram, etc.
        video_domains = ['youtube.com', 'youtu.be', 'instagram.com', 'facebook.com', 
                        'twitter.com', 'tiktok.com', 'vimeo.com', 'dailymotion.com']
        
        is_video_url = any(domain in url_or_file.lower() for domain in video_domains)
        
        if is_video_url:
            return await self.download_ytdlp(url_or_file, progress_callback)
        else:
            return await self.download_file(url_or_file, filename, progress_callback)
    
    def cleanup(self, filepath):
        """Remove downloaded file or directory"""
        try:
            if os.path.isfile(filepath):
                os.remove(filepath)
            elif os.path.isdir(filepath):
                shutil.rmtree(filepath)
        except Exception:
            pass

downloader = Downloader()
