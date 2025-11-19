import os
import aiohttp
import asyncio
import yt_dlp
import libtorrent as lt
from config import Config
from helpers import sanitize_filename
import time
import shutil
import hashlib
import re
import json

# Auxiliary function for formatting file sizes
def format_bytes(size):
    """Format bytes into human-readable string (e.g., 1.2 GB)"""
    power = 2**10
    n = 0
    units = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
    while size > power:
        size /= power
        n += 1
    return f"{size:.2f} {units[n]}"

def truncate_filename(filename, max_length=200):
    """Truncate filename to prevent filesystem errors while preserving extension"""
    name, ext = os.path.splitext(filename)
    
    # Reserve space for extension and some buffer
    max_name_length = max_length - len(ext) - 10
    
    if len(name) > max_name_length:
        # Create hash of full name for uniqueness
        name_hash = hashlib.md5(name.encode()).hexdigest()[:8]
        name = name[:max_name_length - 9] + '_' + name_hash
    
    return name + ext

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
            timeout = aiohttp.ClientTimeout(total=None, connect=30, sock_read=30)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Range': 'bytes=0-'
            }
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
                    
                    if not filename:
                        content_disp = response.headers.get('content-disposition', '')
                        if 'filename=' in content_disp:
                            filename = content_disp.split('filename=')[1].strip('"\'')
                        else:
                            filename = url.split('/')[-1].split('?')[0] or 'downloaded_file'
                    
                    filename = sanitize_filename(filename)
                    filename = truncate_filename(filename)
                    filepath = os.path.join(self.download_dir, filename)
                    
                    downloaded = 0
                    start_time = time.time()
                    last_update = 0
                    chunk_size = 10 * 1024 * 1024
                    
                    with open(filepath, 'wb') as f:
                        async for chunk in response.content.iter_chunked(chunk_size):
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            current_time = time.time()
                            if progress_callback and (current_time - last_update) >= 1:
                                last_update = current_time
                                speed = downloaded / (current_time - start_time) / (1024 * 1024)
                                await progress_callback(downloaded, total_size, f"Downloading ({speed:.1f} MB/s)")
                    
                    return filepath, None
                    
        except asyncio.TimeoutError:
            return None, "Download timeout - server too slow"
        except aiohttp.ClientError as e:
            return None, f"Network error: {str(e)}"
        except Exception as e:
            return None, f"Download error: {str(e)}"

    async def download_tiktok_fallback(self, url, progress_callback=None):
        """Fallback method to download TikTok videos using direct API approach"""
        try:
            # Extract video ID from URL
            video_id = None
            patterns = [
                r'tiktok\.com.*?/video/(\d+)',
                r'tiktok\.com.*?/v/(\d+)',
                r'vm\.tiktok\.com/([A-Za-z0-9]+)',
                r'vt\.tiktok\.com/([A-Za-z0-9]+)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    video_id = match.group(1)
                    break
            
            if not video_id:
                return None, "Could not extract TikTok video ID"
            
            # Try to get the actual video URL
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'Referer': 'https://www.tiktok.com/',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            }
            
            async with aiohttp.ClientSession() as session:
                # First, try to resolve short URLs
                if 'vm.tiktok.com' in url or 'vt.tiktok.com' in url:
                    async with session.get(url, headers=headers, allow_redirects=True) as resp:
                        url = str(resp.url)
                
                # Try OEmbed API (official TikTok API)
                oembed_url = f"https://www.tiktok.com/oembed?url={url}"
                try:
                    async with session.get(oembed_url, headers=headers) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            title = data.get('title', f'tiktok_{video_id}')
                            # OEmbed doesn't give direct video URL, but confirms video exists
                except:
                    pass
                
                # Try alternative download APIs
                api_urls = [
                    f"https://api16-normal-c-useast1a.tiktokv.com/aweme/v1/feed/?aweme_id={video_id}",
                    f"https://api22-normal-c-useast2a.tiktokv.com/aweme/v1/feed/?aweme_id={video_id}",
                ]
                
                for api_url in api_urls:
                    try:
                        async with session.get(api_url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                aweme_list = data.get('aweme_list', [])
                                if aweme_list:
                                    video_data = aweme_list[0].get('video', {})
                                    play_addr = video_data.get('play_addr', {})
                                    url_list = play_addr.get('url_list', [])
                                    
                                    if url_list:
                                        video_url = url_list[0]
                                        filename = f"tiktok_{video_id}.mp4"
                                        return await self.download_file(video_url, filename, progress_callback)
                    except:
                        continue
            
            return None, "TikTok API extraction failed"
            
        except Exception as e:
            return None, f"TikTok fallback error: {str(e)}"

    async def download_ytdlp(self, url, progress_callback=None):
        """Download using yt-dlp with BEST quality - Enhanced TikTok support"""
        try:
            # Check yt-dlp version and warn if outdated
            try:
                ytdlp_version = yt_dlp.version.__version__
                year = int(ytdlp_version.split('.')[0])
                if year < 2024:
                    print(f"⚠️ Warning: yt-dlp version {ytdlp_version} is outdated. Run: pip install -U yt-dlp")
            except:
                pass
            
            # Check if this is TikTok - use fallback first
            is_tiktok = any(domain in url.lower() for domain in ['tiktok.com', 'vm.tiktok.com', 'vt.tiktok.com'])
            
            if is_tiktok:
                if progress_callback:
                    await progress_callback(0, 100, "Trying TikTok direct download...")
                
                # Try fallback method first
                result, error = await self.download_tiktok_fallback(url, progress_callback)
                if result:
                    return result, None
                
                # If fallback fails, try yt-dlp
                if progress_callback:
                    await progress_callback(0, 100, "Trying alternative method...")
            
            # Generate a short, safe filename template
            url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
            
            ydl_opts = {
                'outtmpl': os.path.join(self.download_dir, f'video_{url_hash}_%(id)s.%(ext)s'),
                'format': 'best[ext=mp4]/best',  # Simplified format for better compatibility
                'merge_output_format': 'mp4',
                'quiet': True,
                'no_warnings': True,
                'writethumbnail': False,
                'no_post_overwrites': True,
                'concurrent_fragment_downloads': 5,
                'buffer_size': 16384,
                'http_chunk_size': 10485760,
                'cookiesfrombrowser': None,
                'nocheckcertificate': True,  # Skip certificate verification
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36',
                    'Accept': '*/*',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Origin': 'https://www.tiktok.com',
                    'Referer': 'https://www.tiktok.com/',
                    'Sec-Fetch-Mode': 'cors',
                    'Sec-Fetch-Site': 'same-site',
                    'Sec-Fetch-Dest': 'empty',
                },
                'extractor_args': {
                    'tiktok': {
                        'api_hostname': 'api16-normal-c-useast1a.tiktokv.com',
                    }
                },
                'retries': 15,
                'fragment_retries': 15,
                'skip_unavailable_fragments': True,
                'keepvideo': False,
                'socket_timeout': 30,
                'source_address': '0.0.0.0',
                'geo_bypass': True,
                'extractor_retries': 10,
                'ignoreerrors': False,
            }
            
            loop = asyncio.get_event_loop()
            
            def download():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    try:
                        info = ydl.extract_info(url, download=True)
                        filename = ydl.prepare_filename(info)
                        
                        # Check multiple possible output files
                        base = os.path.splitext(filename)[0]
                        possible_files = [
                            filename,
                            f"{base}.mp4",
                            f"{base}.mkv",
                            f"{base}.webm",
                        ]
                        
                        # Also check the directory for the most recent file with our hash
                        for file in os.listdir(self.download_dir):
                            if url_hash in file and file.endswith(('.mp4', '.mkv', '.webm')):
                                possible_files.append(os.path.join(self.download_dir, file))
                        
                        for pfile in possible_files:
                            if os.path.exists(pfile):
                                return pfile, info.get('title', 'Video')
                        
                        return filename, info.get('title', 'Video')
                    
                    except yt_dlp.utils.DownloadError as e:
                        error_msg = str(e)
                        # Check if it's a TikTok-specific error
                        if 'TikTok' in error_msg:
                            raise Exception(f"TikTok download failed - the video may be private, geo-restricted, or unavailable. Try updating yt-dlp: pip install -U yt-dlp")
                        raise
            
            filepath, title = await loop.run_in_executor(None, download)
            
            if os.path.exists(filepath):
                return filepath, None
            else:
                return None, "Failed to download video - file not found after download"
                
        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            if 'unable to open for writing' in error_msg and 'File name too long' in error_msg:
                return None, "Filename too long error - please try again (using shorter filename now)"
            elif 'Unable to extract' in error_msg or 'webpage video data' in error_msg:
                # For TikTok, suggest alternative solutions
                if any(domain in url.lower() for domain in ['tiktok.com', 'vm.tiktok.com', 'vt.tiktok.com']):
                    return None, "❌ TikTok download failed after trying multiple methods.\n\n🔧 Solutions:\n1. Update yt-dlp: pip install -U yt-dlp\n2. Check if video is private/age-restricted\n3. Try copying the link again\n4. Video may be geo-blocked in your region"
                return None, f"Failed to extract video: {str(e)}"
            return None, f"yt-dlp download error: {str(e)}"
        except Exception as e:
            error_msg = str(e)
            if 'TikTok download failed' in error_msg:
                return None, error_msg
            return None, f"Download error: {str(e)}"

    async def download_torrent(self, magnet_or_file, progress_callback=None):
        """Download torrent using libtorrent with optimized settings"""
        ses = None
        handle = None
        try:
            # Setup Session
            ses = lt.session({'listen_interfaces': '0.0.0.0:6881'})
            ses.add_dht_router('router.bittorrent.com', 6881)
            ses.add_dht_router('router.utorrent.com', 6881)
            ses.add_dht_router('dht.transmissionbt.com', 6881)
            
            settings = {
                'connections_limit': 400,
                'alert_mask': lt.alert.category_t.error_notification | 
                             lt.alert.category_t.storage_notification | 
                             lt.alert.category_t.status_notification
            }
            ses.apply_settings(settings)

            # Setup Add Parameters
            if magnet_or_file.startswith('magnet:'):
                p = lt.parse_magnet_uri(magnet_or_file)
            else:
                if not os.path.exists(magnet_or_file):
                    return None, "Torrent file not found"
                p = lt.add_torrent_params()
                info = lt.torrent_info(magnet_or_file)
                p.ti = info
            
            p.save_path = self.torrent_dir
            p.storage_mode = lt.storage_mode_t.storage_mode_sparse
            p.flags = lt.torrent_flags.auto_managed

            # Add Torrent
            handle = ses.add_torrent(p)
            
            # Download Loop
            metadata_timeout = 180
            download_timeout = 7200
            start_time = time.time()
            last_progress = -1
            metadata_received = False
            
            while not handle.is_seed():
                if time.time() - start_time > download_timeout:
                    return None, "Torrent download timed out after 2 hours"
                
                s = handle.status()

                # Process alerts
                alerts = ses.pop_alerts()
                for alert in alerts:
                    if isinstance(alert, lt.torrent_error_alert):
                        return None, f"Torrent error: {alert.message()}"
                    if isinstance(alert, lt.metadata_failed_alert):
                        return None, "Failed to fetch metadata (no peers/dead torrent)"
                    if isinstance(alert, lt.metadata_received_alert):
                        metadata_received = True
                
                # Progress Reporting
                if not handle.has_metadata():
                    elapsed = time.time() - start_time
                    if elapsed > metadata_timeout:
                        return None, "Timeout waiting for torrent metadata (3 min)"

                    status_msg = f"Connecting... ({s.num_peers} peers)"
                    if progress_callback:
                        await progress_callback(0, 100, status_msg)
                
                else:
                    if not metadata_received:
                        metadata_received = True
                    
                    info = handle.get_torrent_info()
                    total_size = info.total_size()
                    
                    if total_size > Config.MAX_FILE_SIZE:
                        return None, f"Torrent size ({format_bytes(total_size)}) exceeds limit"
                    
                    progress = s.progress * 100
                    download_rate = s.download_rate / 1024 / 1024
                    
                    if progress_callback and abs(progress - last_progress) >= 1:
                        last_progress = progress
                        status_msg = f"Torrenting | ↓ {download_rate:.1f} MB/s | {s.num_peers} peers | {progress:.1f}%"
                        await progress_callback(int(s.total_done), total_size, status_msg)

                await asyncio.sleep(1)

            # Finalize
            info = handle.get_torrent_info()
            name = info.name()

            if info.num_files() == 1:
                filepath = os.path.join(self.torrent_dir, info.files().file_path(0))
            else:
                filepath = os.path.join(self.torrent_dir, name)
            
            return filepath, None
            
        except Exception as e:
            return None, f"Torrent error: {str(e)}"
        finally:
            if ses and handle and handle.is_valid():
                ses.remove_torrent(handle)

    async def download(self, url_or_file, filename=None, progress_callback=None):
        """Main download function - auto-detects type"""
        
        if not url_or_file:
            return None, "No URL or file provided"
        
        if isinstance(url_or_file, str) and (url_or_file.startswith('magnet:') or url_or_file.endswith('.torrent')):
            return await self.download_torrent(url_or_file, progress_callback)
        
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
