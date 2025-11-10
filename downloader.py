import os
import aiohttp
import asyncio
import yt_dlp
import libtorrent as lt
from config import Config
from helpers import speed_limiter, sanitize_filename
import time

class Downloader:
    def __init__(self):
        self.download_dir = Config.DOWNLOAD_DIR
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
        
        # Initialize torrent session
        self.torrent_session = lt.session()
        self.torrent_session.listen_on(6881, 6891)
    
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
    
    async def download_torrent(self, magnet_or_torrent, progress_callback=None):
        """Download torrent using libtorrent"""
        try:
            # Check if it's a magnet link or torrent file
            if magnet_or_torrent.startswith('magnet:'):
                params = lt.parse_magnet_uri(magnet_or_torrent)
                # Use attribute assignment, not dictionary assignment
                params.save_path = self.download_dir
            else:
                # Assume it's a torrent file path
                params = lt.add_torrent_params()
                params.ti = lt.torrent_info(magnet_or_torrent)
                params.save_path = self.download_dir
            
            # Add torrent to session
            handle = self.torrent_session.add_torrent(params)
            
            print(f"Downloading torrent: {handle.name()}")
            
            # Wait for metadata (for magnet links)
            while not handle.has_metadata():
                await asyncio.sleep(0.1)
            
            print(f"Got metadata, starting download: {handle.name()}")
            
            # Monitor download progress
            while not handle.is_seed():
                status = handle.status()
                
                progress = status.progress * 100
                download_rate = status.download_rate / 1000  # KB/s
                num_peers = status.num_peers
                
                if progress_callback:
                    await progress_callback(
                        status.total_done,
                        status.total_wanted,
                        f"Downloading (Peers: {num_peers}, Speed: {download_rate:.1f} KB/s)"
                    )
                
                # Check if paused or has error
                if status.paused:
                    return None, "Download paused or failed"
                
                await asyncio.sleep(1)
            
            # Get the downloaded file path
            torrent_info = handle.get_torrent_info()
            if torrent_info.num_files() == 1:
                filepath = os.path.join(self.download_dir, torrent_info.files().file_path(0))
            else:
                # Multiple files, return directory
                filepath = os.path.join(self.download_dir, handle.name())
            
            print(f"Download complete: {filepath}")
            return filepath, None
            
        except Exception as e:
            return None, f"Torrent error: {str(e)}"
    
    async def download(self, url, filename=None, progress_callback=None):
        """Main download function - chooses appropriate method"""
        
        # Check if it's a magnet link
        if url.startswith('magnet:'):
            return await self.download_torrent(url, progress_callback)
        
        # Check if it's a torrent file
        if url.endswith('.torrent'):
            # Download the torrent file first, then use it
            torrent_file, error = await self.download_file(url, 'temp.torrent')
            if error:
                return None, error
            result = await self.download_torrent(torrent_file, progress_callback)
            self.cleanup(torrent_file)
            return result
        
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
