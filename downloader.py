import os
import aiohttp
import asyncio
import yt_dlp
import libtorrent as lt
from config import Config
from helpers import sanitize_filename
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
        """Download file from URL using aiohttp with maximum speed - preserves original quality"""
        try:
            # Optimized timeout settings
            timeout = aiohttp.ClientTimeout(total=None, connect=30, sock_read=30)
            
            # Optimized headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Range': 'bytes=0-'  # Enable range requests for resuming
            }
            
            # Use TCP connector with optimized settings
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=30,
                ttl_dns_cache=300,
                force_close=False,
                enable_cleanup_closed=True
            )
            
            async with aiohttp.ClientSession(
                timeout=timeout, 
                headers=headers,
                connector=connector
            ) as session:
                async with session.get(url, allow_redirects=True) as response:
                    if response.status not in (200, 206):
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
                    
                    # Larger chunk size for faster downloads (10 MB chunks)
                    chunk_size = 10 * 1024 * 1024  # 10 MB
                    
                    # Write in binary mode to preserve original file
                    with open(filepath, 'wb') as f:
                        async for chunk in response.content.iter_chunked(chunk_size):
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            # Progress callback every 1 second
                            current_time = time.time()
                            if progress_callback and (current_time - last_update) >= 1:
                                last_update = current_time
                                speed = downloaded / (current_time - start_time) / (1024 * 1024)
                                await progress_callback(downloaded, total_size, f"Downloading ({speed:.1f} MB/s)")
                            
                            # No artificial delays for maximum speed
                    
                    return filepath, None
                    
        except asyncio.TimeoutError:
            return None, "Download timeout - server too slow"
        except aiohttp.ClientError as e:
            return None, f"Network error: {str(e)}"
        except Exception as e:
            return None, f"Download error: {str(e)}"
    
    async def download_ytdlp(self, url, progress_callback=None):
        """Download using yt-dlp with BEST quality - ORIGINAL file + TikTok support"""
        try:
            # Enhanced options for maximum speed and quality
            ydl_opts = {
                'outtmpl': os.path.join(self.download_dir, '%(title)s.%(ext)s'),
                'format': 'bestvideo+bestaudio/best',
                'merge_output_format': 'mp4',
                'quiet': True,
                'no_warnings': True,
                'writethumbnail': False,
                'no_post_overwrites': True,
                # Speed optimizations
                'concurrent_fragment_downloads': 5,  # Download multiple fragments simultaneously
                'buffer_size': 16384,  # 16 KB buffer
                'http_chunk_size': 10485760,  # 10 MB chunks
                # Enhanced headers for TikTok and better compatibility
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-us,en;q=0.5',
                    'Sec-Fetch-Mode': 'navigate',
                    'Referer': 'https://www.tiktok.com/'
                },
                # TikTok specific options
                'extractor_args': {
                    'tiktok': {
                        'api_hostname': 'api22-normal-c-useast2a.tiktokv.com',
                        'app_version': '34.1.2',
                        'manifest_app_version': '341'
                    }
                },
                # Enhanced retry options
                'retries': 15,
                'fragment_retries': 15,
                'skip_unavailable_fragments': True,
                'keepvideo': False,  # Don't keep separate video/audio files
                # Network optimizations
                'socket_timeout': 30,
                'source_address': '0.0.0.0',
                # Postprocessing optimizations
                'postprocessor_args': {
                    'ffmpeg': ['-threads', '4']  # Use 4 threads for ffmpeg
                }
            }
            
            loop = asyncio.get_event_loop()
            
            def download():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    filename = ydl.prepare_filename(info)
                    
                    # Check for merged file
                    base = os.path.splitext(filename)[0]
                    possible_files = [
                        f"{base}.mp4",
                        f"{base}.mkv",
                        f"{base}.webm",
                        filename
                    ]
                    
                    for pfile in possible_files:
                        if os.path.exists(pfile):
                            return pfile, info.get('title', 'Video')
                    
                    return filename, info.get('title', 'Video')
            
            filepath, title = await loop.run_in_executor(None, download)
            
            if os.path.exists(filepath):
                return filepath, None
            else:
                return None, "Failed to download video - file not found after download"
                
        except yt_dlp.utils.DownloadError as e:
            return None, f"yt-dlp download error: {str(e)}"
        except Exception as e:
            return None, f"Download error: {str(e)}"
    
    async def download_torrent(self, magnet_or_file, progress_callback=None):
        """Download torrent using libtorrent with optimized settings"""
        try:
            # Create session with optimized settings
            ses = lt.session()
            ses.listen_on(6881, 6891)
            
            # Apply speed optimizations
            settings = {
                'download_rate_limit': 0,  # Unlimited
                'upload_rate_limit': 1024 * 100,  # Limit upload to 100 KB/s
                'connections_limit': 200,
                'active_downloads': 10,
                'active_seeds': 5,
                'max_failcount': 1,
                'request_timeout': 10,
                'peer_connect_timeout': 10,
                'read_cache_line_size': 256,
                'write_cache_line_size': 256,
                'alert_queue_size': 2000,
            }
            ses.apply_settings(settings)
            
            params = {
                'save_path': self.torrent_dir,
                'storage_mode': lt.storage_mode_t.storage_mode_sparse,
            }
            
            # Check if it's a magnet link or file
            if magnet_or_file.startswith('magnet:'):
                handle = lt.add_magnet_uri(ses, magnet_or_file, params)
            else:
                # It's a torrent file path
                if not os.path.exists(magnet_or_file):
                    return None, "Torrent file not found"
                info = lt.torrent_info(magnet_or_file)
                handle = ses.add_torrent({'ti': info, 'save_path': self.torrent_dir})
            
            # Wait for metadata with timeout
            metadata_timeout = 60  # 60 seconds
            start = time.time()
            while not handle.has_metadata():
                if time.time() - start > metadata_timeout:
                    ses.remove_torrent(handle)
                    return None, "Timeout waiting for torrent metadata"
                await asyncio.sleep(0.5)
            
            info = handle.get_torrent_info()
            name = info.name()
            
            # Download with progress updates
            last_progress = -1
            while not handle.is_seed():
                s = handle.status()
                
                progress = s.progress * 100
                download_rate = s.download_rate / 1024 / 1024  # MB/s
                
                # Only update if progress changed significantly
                if progress_callback and abs(progress - last_progress) >= 1:
                    last_progress = progress
                    await progress_callback(
                        int(s.total_done),
                        int(s.total_wanted),
                        f"Torrenting ({download_rate:.2f} MB/s, {progress:.1f}%)"
                    )
                
                # Check if torrent has error
                if s.error:
                    ses.remove_torrent(handle)
                    return None, f"Torrent error: {s.error}"
                
                await asyncio.sleep(1)
            
            # Get downloaded file path
            filepath = os.path.join(self.torrent_dir, name)
            
            # Stop seeding
            ses.remove_torrent(handle)
            
            if os.path.exists(filepath):
                return filepath, None
            else:
                return None, "Downloaded file not found"
            
        except Exception as e:
            return None, f"Torrent error: {str(e)}"
    
    async def download(self, url_or_file, filename=None, progress_callback=None):
        """Main download function - auto-detects type"""
        
        if not url_or_file:
            return None, "No URL or file provided"
        
        # Check if it's a magnet link
        if isinstance(url_or_file, str) and url_or_file.startswith('magnet:'):
            return await self.download_torrent(url_or_file, progress_callback)
        
        # Check if it's a torrent file
        if isinstance(url_or_file, str) and url_or_file.endswith('.torrent'):
            return await self.download_torrent(url_or_file, progress_callback)
        
        # Check if URL is for YouTube, Instagram, TikTok, etc.
        video_domains = [
            'youtube.com', 'youtu.be', 'instagram.com', 'facebook.com', 
            'twitter.com', 'tiktok.com', 'vimeo.com', 'dailymotion.com',
            'vt.tiktok.com', 'vm.tiktok.com', 'x.com', 'twitch.tv',
            'reddit.com', 'streamable.com', 'imgur.com'
        ]
        
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
            return True
        except Exception as e:
            print(f"Cleanup error: {e}")
            return False

downloader = Downloader()
