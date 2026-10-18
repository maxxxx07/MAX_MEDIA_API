from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
import requests
import uuid
import re

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl, Field
from yt_dlp import YoutubeDL
APP_NAME = "MAX MEDIA Master API"
APP_VERSION = "1.0.0"

app = FastAPI(
    title=APP_NAME,
    description=(
        "Shared backend API for MAX MEDIA "
        "Telegram bot, website and Android app."
    ),
    version=APP_VERSION,
)

# Local testing only. Production mein origins restrict karna.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "project": "MAX MEDIA",
        "service": APP_NAME,
        "version": APP_VERSION,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/api/v1/health")
def health():
    return {
        "status": "healthy",
        "service": APP_NAME,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/v1/version")
def version():
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "api_prefix": "/api/v1",
    }


@app.get("/api/v1/platforms")
def platforms():
    return {
        "platforms": [
            {
                "id": "youtube",
                "name": "YouTube",
                "enabled": True,
                "note": "Video info, formats, video and audio downloads",
            },
            {
                "id": "instagram",
                "name": "Instagram",
                "enabled": True,
                "note": "Profile, DP and Reels; Stories and Highlights may have limitations",
            },
            {
                "id": "facebook",
                "name": "Facebook",
                "enabled": True,
                "note": "Video info, formats, video and audio; some content may require login",
            },
            {
                "id": "pinterest",
                "name": "Pinterest",
                "enabled": True,
                "note": "Image and supported media downloads",
            },
            {
                "id": "snapchat",
                "name": "Snapchat",
                "enabled": True,
                "note": "Spotlight video downloads; availability depends on the link",
            },
            {
                "id": "chrome",
                "name": "Chrome / Direct Link",
                "enabled": True,
                "note": "Supported direct media URLs",
            },
        ]
    }

class YouTubeInfoRequest(BaseModel):
    url: HttpUrl


@app.post("/api/v1/youtube/info")
def youtube_info(request: YouTubeInfoRequest):
    url = str(request.url)
    hostname = request.url.host.lower()

    # Sirf YouTube ke recognized hostnames accept karo.
    allowed_hosts = {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "youtu.be",
        "www.youtube-nocookie.com",
    }

    if hostname not in allowed_hosts:
        raise HTTPException(
            status_code=400,
            detail="Please provide a valid YouTube URL.",
        )

    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "socket_timeout": 10,
    }

    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)

        return {
            "status": "success",
            "platform": "YouTube",
            "title": info.get("title"),
            "duration_seconds": info.get("duration"),
            "uploader": info.get("uploader"),
            "webpage_url": info.get("webpage_url"),
        }

    except Exception as e:
        print("YT-DLP ERROR:", repr(e))
        raise HTTPException(
            status_code=400,
            detail="Video information could not be retrieved.",
        )
@app.post("/api/v1/youtube/formats")
def youtube_formats(request: YouTubeInfoRequest):
    url = str(request.url)
    hostname = request.url.host.lower()

    allowed_hosts = {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "youtu.be",
        "www.youtube-nocookie.com",
    }

    if hostname not in allowed_hosts:
        raise HTTPException(
            status_code=400,
            detail="Please provide a valid YouTube URL.",
        )

    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "socket_timeout": 10,
    }

    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)

        formats = [
            {
                "format_id": item.get("format_id"),
                "ext": item.get("ext"),
                "resolution": item.get("resolution"),
                "filesize": item.get("filesize"),
                "has_video": item.get("vcodec") != "none",
                "has_audio": item.get("acodec") != "none",
            }
            for item in info.get("formats", [])
        ]

        return {
            "status": "success",
            "platform": "YouTube",
            "title": info.get("title"),
            "formats": formats,
        }

    except Exception as e:
        print("YT-DLP FORMATS ERROR:", repr(e))
        raise HTTPException(
            status_code=400,
            detail="Video formats could not be retrieved.",
        )
    
class YouTubeDownloadRequest(BaseModel):
    url: HttpUrl


def download_youtube(url: str, audio_only: bool = False):
    from pathlib import Path
    from urllib.parse import urlparse

    allowed_hosts = {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "youtu.be",
        "www.youtube-nocookie.com",
    }

    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or (parsed.hostname or "").lower() not in allowed_hosts
    ):
        raise HTTPException(
            status_code=400,
            detail="Please provide a valid YouTube HTTPS URL.",
        )

    folder = Path("downloads") / "youtube"
    folder.mkdir(parents=True, exist_ok=True)

    options = {
    "format": "bestaudio/best" if audio_only else "bestvideo*+bestaudio/best",
    "ffmpeg_location": r"C:\Users\ASUS\Downloads\ffmpeg-9.0.2-essentials_build\ffmpeg-9.0.2-essentials_build\bin",
    "outtmpl": str(folder / "%(title).100B [%(id)s].%(ext)s"),
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "socket_timeout": 20,
    "retries": 2,
}

    if audio_only:
        options["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
    else:
        options["merge_output_format"] = "mp4"

    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            expected = Path(ydl.prepare_filename(info))

        candidates = (
            [expected.with_suffix(".mp3")]
            if audio_only
            else [expected.with_suffix(".mp4"), expected]
        )
        output = next((p for p in candidates if p.is_file()), None)

        if output is None:
            matches = list(folder.glob(f"*[{info['id']}]*"))
            matches = [p for p in matches if p.is_file()]
            if not matches:
                raise RuntimeError("Downloaded file was not found.")
            output = max(matches, key=lambda p: p.stat().st_mtime)

        return {
            "status": "success",
            "platform": "YouTube",
            "type": "audio_mp3" if audio_only else "video",
            "title": info.get("title"),
            "saved_to": str(output.resolve()),
            "size_bytes": output.stat().st_size,
            "note": "File is saved locally on the API server.",
        }

    except HTTPException:
        raise
    except Exception as exc:
        print("YOUTUBE DOWNLOAD ERROR:", repr(exc))
        raise HTTPException(
            status_code=400,
            detail="Download failed. Check the URL, format availability and FFmpeg setup.",
        )


@app.post("/api/v1/youtube/download/video")
def youtube_download_video(request: YouTubeDownloadRequest):
    return download_youtube(str(request.url), audio_only=False)


@app.post("/api/v1/youtube/download/audio")
def youtube_download_audio(request: YouTubeDownloadRequest):
    return download_youtube(str(request.url), audio_only=True)

    

from pathlib import Path
from urllib.parse import urlparse

import requests
import instaloader
from pydantic import BaseModel, HttpUrl
from yt_dlp import YoutubeDL


@app.get("/api/v1/instagram/profile")
def instagram_profile(username: str):
    username = username.strip().lstrip("@")

    if not username or "/" in username or " " in username:
        raise HTTPException(status_code=400, detail="Please provide a valid Instagram username.")

    try:
        loader = instaloader.Instaloader()
        profile = instaloader.Profile.from_username(loader.context, username)

        return {
            "status": "success",
            "platform": "Instagram",
            "username": profile.username,
            "full_name": profile.full_name,
            "is_private": profile.is_private,
            "profile_picture_available": bool(profile.profile_pic_url),
            "profile_picture_url": str(profile.profile_pic_url),
            "profile_url": f"https://www.instagram.com/{profile.username}/",
        }
    except Exception as e:
        print("INSTAGRAM PROFILE ERROR:", repr(e))
        raise HTTPException(status_code=400, detail="Instagram profile information could not be retrieved.")


@app.get("/api/v1/instagram/dp")
def instagram_download_dp(username: str):
    username = username.strip().lstrip("@")

    if (
        not username
        or len(username) > 30
        or not username.replace(".", "").replace("_", "").isalnum()
    ):
        raise HTTPException(status_code=400, detail="Please provide a valid Instagram username.")

    try:
        loader = instaloader.Instaloader()
        profile = instaloader.Profile.from_username(loader.context, username)
        image_url = str(profile.profile_pic_url)
        host = urlparse(image_url).hostname or ""

        if not host.endswith(".cdninstagram.com"):
            raise HTTPException(status_code=400, detail="Unexpected profile picture URL.")

        response = requests.get(
            image_url,
            timeout=20,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        response.raise_for_status()

        final_host = urlparse(response.url).hostname or ""
        if not final_host.endswith(".cdninstagram.com"):
            raise HTTPException(status_code=400, detail="Unexpected download destination.")

        if not response.headers.get("Content-Type", "").startswith("image/"):
            raise HTTPException(status_code=400, detail="Instagram did not return an image.")

        folder = Path("downloads") / "instagram"
        folder.mkdir(parents=True, exist_ok=True)
        file_path = folder / f"{profile.username}_dp.jpg"
        file_path.write_bytes(response.content)

        return {
            "status": "success",
            "username": profile.username,
            "saved_to": str(file_path.resolve()),
            "size_bytes": len(response.content),
        }
    except HTTPException:
        raise
    except Exception as e:
        print("INSTAGRAM DP DOWNLOAD ERROR:", repr(e))
        raise HTTPException(status_code=400, detail="Public Instagram DP download failed. Try again later.")


class InstagramReelRequest(BaseModel):
    url: HttpUrl


@app.post("/api/v1/instagram/reels/download")
def instagram_reel_download(request: InstagramReelRequest):
    reel_url = str(request.url)
    parsed = urlparse(reel_url)
    host = (parsed.hostname or "").lower()

    if parsed.scheme != "https" or host not in {"instagram.com", "www.instagram.com", "m.instagram.com"}:
        raise HTTPException(status_code=400, detail="Please provide a valid Instagram HTTPS Reel URL.")

    if not parsed.path.startswith(("/reel/", "/reels/", "/p/")):
        raise HTTPException(status_code=400, detail="Please provide an Instagram Reel or post URL.")

    folder = Path("downloads") / "instagram" / "reels"
    folder.mkdir(parents=True, exist_ok=True)

    options = {
        "format": "best",
        "outtmpl": str(folder / "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 20,
        "retries": 2,
    }

    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(reel_url, download=True)
            file_path = Path(ydl.prepare_filename(info))

        if not file_path.is_file():
            matches = list(folder.glob(f"{info['id']}.*"))
            if not matches:
                raise RuntimeError("Downloaded file was not found.")
            file_path = matches[0]

        return {
            "status": "success",
            "platform": "Instagram",
            "type": "reel_video",
            "title": info.get("title"),
            "saved_to": str(file_path.resolve()),
            "size_bytes": file_path.stat().st_size,
            "note": "Saved locally on the API server.",
        }
    except Exception as e:
        print("INSTAGRAM REEL DOWNLOAD ERROR:", repr(e))
        raise HTTPException(status_code=400, detail="Reel download failed. Check URL, permissions and yt-dlp support.")


class InstagramStoryRequest(BaseModel):
    url: HttpUrl


@app.post("/api/v1/instagram/story/download")
def instagram_story_download(request: InstagramStoryRequest):
    story_url = str(request.url)
    parsed = urlparse(story_url)
    host = (parsed.hostname or "").lower()

    if parsed.scheme != "https" or host not in {"instagram.com", "www.instagram.com", "m.instagram.com"}:
        raise HTTPException(status_code=400, detail="Invalid Instagram HTTPS URL.")

    if not parsed.path.startswith("/stories/"):
        raise HTTPException(status_code=400, detail="Please provide an Instagram Story URL.")

    folder = Path("downloads") / "instagram" / "stories"
    folder.mkdir(parents=True, exist_ok=True)

    options = {
        "format": "best",
        "outtmpl": str(folder / "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 20,
        "retries": 2,
    }

    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(story_url, download=True)
            file_path = Path(ydl.prepare_filename(info))

        if not file_path.is_file():
            matches = list(folder.glob(f"{info['id']}.*"))
            if not matches:
                raise RuntimeError("Downloaded file was not found.")
            file_path = matches[0]

        return {
            "status": "success",
            "platform": "Instagram",
            "type": "story",
            "saved_to": str(file_path.resolve()),
            "size_bytes": file_path.stat().st_size,
            "note": "Saved locally on the API server.",
        }
    except Exception as e:
        print("INSTAGRAM STORY DOWNLOAD ERROR:", repr(e))
        raise HTTPException(status_code=400, detail="Story download failed. Check URL, account access and yt-dlp support.")


class InstagramHighlightsRequest(BaseModel):
    url: HttpUrl


@app.post("/api/v1/instagram/highlights/download")
def instagram_highlights_download(request: InstagramHighlightsRequest):
    highlights_url = str(request.url)
    parsed = urlparse(highlights_url)
    host = (parsed.hostname or "").lower()

    if (
        parsed.scheme != "https"
        or host not in {
            "instagram.com",
            "www.instagram.com",
            "m.instagram.com",
        }
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid Instagram HTTPS URL.",
        )

    is_highlights_url = (
        parsed.path.startswith("/stories/highlights/")
        or (
            parsed.path.startswith("/s/")
            and "story_media_id" in parsed.query
        )
    )

    if not is_highlights_url:
        raise HTTPException(
            status_code=400,
            detail="Please provide a valid Instagram Highlights URL.",
        )

    folder = Path("downloads") / "instagram" / "highlights"
    folder.mkdir(parents=True, exist_ok=True)

    options = {
        "format": "best",
        "outtmpl": str(folder / "%(id)s.%(ext)s"),
        "noplaylist": False,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 20,
        "retries": 2,
    }

    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(highlights_url, download=True)

        entries = info.get("entries") if info else None
        if entries is None:
            entries = [info] if info else []

        downloaded_files = []
        for entry in entries:
            if not entry:
                continue

            filename = ydl.prepare_filename(entry)
            file_path = Path(filename)

            if file_path.is_file():
                downloaded_files.append({
                    "file": str(file_path.resolve()),
                    "file_name": file_path.name,
                    "size_bytes": file_path.stat().st_size,
                })

        if not downloaded_files:
            raise HTTPException(
                status_code=404,
                detail=(
                    "No highlight media was downloaded. "
                    "Instagram may require login or restrict access."
                ),
            )

        return {
            "status": "success",
            "platform": "Instagram",
            "type": "highlights",
            "downloaded_count": len(downloaded_files),
            "files": downloaded_files,
            "note": "Files are saved locally on the API server.",
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "Could not download Highlights. Instagram may require "
                f"login or restrict access. Error: {str(exc)[:250]}"
            ),
        )

    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(highlights_url, download=True)

        return {
            "status": "success",
            "platform": "Instagram",
            "type": "highlights",
            "title": info.get("title"),
            "note": "Check downloads/instagram/highlights for saved files.",
        }
    except Exception as e:
        print("INSTAGRAM HIGHLIGHTS DOWNLOAD ERROR:", repr(e))
        raise HTTPException(status_code=400, detail="Highlights download failed. Check URL, account access and yt-dlp support.")
# ==============================
# FACEBOOK VIDEO DOWNLOADER
# ==============================

class FacebookDownloadRequest(BaseModel):
    url: HttpUrl


@app.post("/api/v1/facebook/download")
def download_facebook_video(request: FacebookDownloadRequest):
    folder = Path("downloads/facebook")
    folder.mkdir(parents=True, exist_ok=True)

    video_url = str(request.url)

    if not any(
        domain in urlparse(video_url).netloc.lower()
        for domain in ("facebook.com", "fb.watch")
    ):
        raise HTTPException(
            status_code=400,
            detail="Please provide a valid Facebook video URL."
        )

    options = {
        "format": "best",
        "outtmpl": str(folder / "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(video_url, download=True)
            filename = ydl.prepare_filename(info)

        return {
            "success": True,
            "platform": "Facebook",
            "title": info.get("title"),
            "file": filename,
            "message": "Video downloaded successfully."
        }

    except Exception as exc:
        print("FACEBOOK DOWNLOAD ERROR:", repr(exc))
        raise HTTPException(
            status_code=400,
            detail="Facebook download failed. Check the URL and content access."
        )
    
# ==============================
# FACEBOOK VIDEO INFO
# ==============================

class FacebookInfoRequest(BaseModel):
    url: HttpUrl


@app.post("/api/v1/facebook/info")
def facebook_info(request: FacebookInfoRequest):
    url = str(request.url)
    hostname = request.url.host.lower()

    allowed_hosts = {
        "facebook.com",
        "www.facebook.com",
        "m.facebook.com",
        "web.facebook.com",
        "fb.watch",
    }

    if hostname not in allowed_hosts:
        raise HTTPException(
            status_code=400,
            detail="Please provide a valid Facebook URL."
        )

    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
    }

    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)

        formats = []
        for item in info.get("formats", []):
            if item.get("vcodec") != "none":
                formats.append({
                    "format_id": item.get("format_id"),
                    "ext": item.get("ext"),
                    "resolution": item.get("resolution"),
                    "filesize": item.get("filesize"),
                    "format_note": item.get("format_note"),
                })

        return {
            "success": True,
            "platform": "Facebook",
            "title": info.get("title"),
            "duration": info.get("duration"),
            "thumbnail": info.get("thumbnail"),
            "webpage_url": info.get("webpage_url"),
            "available_video_formats": formats,
        }

    except Exception as exc:
        print("FACEBOOK INFO ERROR:", repr(exc))
        raise HTTPException(
            status_code=400,
            detail="Could not fetch Facebook video info. Check the URL and content access."
        )


# ==============================
# FACEBOOK AVAILABLE FORMATS
# ==============================

@app.post("/api/v1/facebook/formats")
def facebook_formats(request: FacebookInfoRequest):
    result = facebook_info(request)
    return {
        "success": result["success"],
        "platform": result["platform"],
        "title": result["title"],
        "available_video_formats": result["available_video_formats"],
    }

# ==============================
# FACEBOOK AUDIO DOWNLOADER
# ==============================

@app.post("/api/v1/facebook/download/audio")
def download_facebook_audio(request: FacebookInfoRequest):
    url = str(request.url)
    hostname = request.url.host.lower()

    allowed_hosts = {
        "facebook.com",
        "www.facebook.com",
        "m.facebook.com",
        "web.facebook.com",
        "fb.watch",
    }

    if hostname not in allowed_hosts:
        raise HTTPException(
            status_code=400,
            detail="Please provide a valid Facebook URL."
        )

    folder = Path("downloads/facebook/audio")
    folder.mkdir(parents=True, exist_ok=True)

    options = {
        "format": "bestaudio/best",
        "outtmpl": str(folder / "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "ffmpeg_location": (
            r"C:\Users\ASUS\Downloads\ffmpeg-9.0.2-essentials_build"
            r"\ffmpeg-9.0.2-essentials_build\bin\ffmpeg.exe"
        ),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }

    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)

        audio_id = info.get("id")
        audio_file = folder / f"{audio_id}.mp3"

        return {
            "success": True,
            "platform": "Facebook",
            "title": info.get("title"),
            "file": str(audio_file),
            "format": "mp3",
            "message": "Audio downloaded successfully.",
        }

    except Exception as exc:
        print("FACEBOOK AUDIO DOWNLOAD ERROR:", repr(exc))
        raise HTTPException(
            status_code=400,
            detail=(
                "Facebook audio download failed. "
                "Check the URL, content access and FFmpeg setup."
            ),
        )

class FacebookVideoFormatDownloadRequest(BaseModel):
    url: HttpUrl
    format_id: str


@app.post("/api/v1/facebook/download/selected")
def facebook_download_selected(request: FacebookVideoFormatDownloadRequest):
    try:
        url = str(request.url)

        output_dir = Path("downloads/facebook/video")
        output_dir.mkdir(parents=True, exist_ok=True)

        ydl_opts = {
            "format": request.format_id,
            "outtmpl": str(output_dir / "%(id)s.%(ext)s"),
            "ffmpeg_location": r"C:\Users\ASUS\Downloads\ffmpeg-9.0.2-essentials_build\ffmpeg-9.0.2-essentials_build\bin\ffmpeg.exe",
            "noplaylist": True,
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

        return {
            "success": True,
            "platform": "Facebook",
            "title": info.get("title"),
            "format_id": request.format_id,
            "file": file_path,
            "message": "Selected video format downloaded successfully."
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class FacebookStoryDownloadRequest(BaseModel):
    url: HttpUrl


@app.post("/api/v1/facebook/story/download")
def facebook_story_download(request: FacebookStoryDownloadRequest):
    try:
        url = str(request.url)
        output_dir = Path("downloads/facebook/stories")
        output_dir.mkdir(parents=True, exist_ok=True)

        ydl_opts = {
            "format": "best",
            "outtmpl": str(output_dir / "%(id)s.%(ext)s"),
            "ffmpeg_location": r"C:\Users\ASUS\Downloads\ffmpeg-9.0.2-essentials_build\ffmpeg-9.0.2-essentials_build\bin\ffmpeg.exe",
            "noplaylist": True,
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

        return {
            "success": True,
            "platform": "Facebook",
            "title": info.get("title"),
            "file": file_path,
            "message": "Facebook Story downloaded successfully.",
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class PinterestDownloadRequest(BaseModel):
    url: HttpUrl


class SnapchatDownloadRequest(BaseModel):
    url: HttpUrl


@app.post("/api/v1/pinterest/download")
def pinterest_download(request: PinterestDownloadRequest):
    try:
        url = str(request.url)
        output_dir = Path("downloads/pinterest")
        output_dir.mkdir(parents=True, exist_ok=True)

        ydl_opts = {
            "format": "best",
            "outtmpl": str(output_dir / "%(id)s.%(ext)s"),
            "noplaylist": True,
            "ffmpeg_location": r"C:\Users\ASUS\Downloads\ffmpeg-9.0.2-essentials_build\ffmpeg-9.0.2-essentials_build\bin\ffmpeg.exe",
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

        extension = Path(file_path).suffix.lower()
        video_extensions = {".mp4", ".webm", ".mkv", ".mov", ".m4v"}
        image_extensions = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

        if extension in video_extensions:
            media_type = "video"
        elif extension in image_extensions:
            media_type = "image"
        else:
            media_type = "unknown"

        return {
            "success": True,
            "platform": "Pinterest",
            "title": info.get("title"),
            "file": file_path,
            "file_name": Path(file_path).name,
            "media_type": media_type,
            "message": "Pinterest media downloaded successfully.",
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/snapchat/spotlight/download")
def snapchat_spotlight_download(request: SnapchatDownloadRequest):
    try:
        url = str(request.url)
        output_dir = Path("downloads/snapchat")
        output_dir.mkdir(parents=True, exist_ok=True)

        ydl_opts = {
            "format": "best",
            "outtmpl": str(output_dir / "%(id)s.%(ext)s"),
            "noplaylist": True,
            "ffmpeg_location": r"C:\Users\ASUS\Downloads\ffmpeg-9.0.2-essentials_build\ffmpeg-9.0.2-essentials_build\bin\ffmpeg.exe",
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

        return {
            "success": True,
            "platform": "Snapchat",
            "title": info.get("title"),
            "file": file_path,
            "file_name": Path(file_path).name,
            "media_type": "video",
            "message": "Snapchat Spotlight video downloaded successfully.",
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class DirectMediaDownloadRequest(BaseModel):
    url: HttpUrl


@app.post("/api/v1/chrome/download")
def chrome_direct_download(request: DirectMediaDownloadRequest):
    try:
        url = str(request.url)

        allowed_hosts = {
            "http",
            "https",
        }

        if url.split(":", 1)[0].lower() not in allowed_hosts:
            raise HTTPException(
                status_code=400,
                detail="Only HTTP and HTTPS URLs are allowed.",
            )

        output_dir = Path("downloads/direct")
        output_dir.mkdir(parents=True, exist_ok=True)

        ydl_opts = {
            "format": "best",
            "outtmpl": str(output_dir / "%(id)s.%(ext)s"),
            "noplaylist": True,
            "socket_timeout": 30,
            "retries": 2,
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

        extension = Path(file_path).suffix.lower()

        video_extensions = {".mp4", ".webm", ".mkv", ".mov", ".m4v"}
        audio_extensions = {".mp3", ".m4a", ".aac", ".wav", ".ogg", ".opus"}
        image_extensions = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

        if extension in video_extensions:
            media_type = "video"
        elif extension in audio_extensions:
            media_type = "audio"
        elif extension in image_extensions:
            media_type = "image"
        else:
            media_type = "unknown"

        return {
            "success": True,
            "platform": "Chrome / Direct Link",
            "title": info.get("title"),
            "file": file_path,
            "file_name": Path(file_path).name,
            "media_type": media_type,
            "message": "Media downloaded successfully.",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class WhatsAppStatusRequest(BaseModel):
    file_name: str = Field(min_length=1, max_length=255)


@app.post("/api/v1/whatsapp/status/import")
def whatsapp_status_import(request: WhatsAppStatusRequest):
    file_name = request.file_name

    if (
        file_name in {".", ".."}
        or "/" in file_name
        or "\\" in file_name
        or not re.fullmatch(r"[A-Za-z0-9 _.-]+", file_name)
    ):
        raise HTTPException(status_code=400, detail="Invalid file name.")

    base_dir = Path("downloads/whatsapp_status").resolve()
    file_path = (base_dir / file_name).resolve()

    if file_path.parent != base_dir or not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="File not found. Place your authorized status media in downloads/whatsapp_status first.",
        )

    allowed_extensions = {
        ".mp4", ".jpg", ".jpeg", ".png", ".webp", ".gif"
    }

    if file_path.suffix.lower() not in allowed_extensions:
        raise HTTPException(
            status_code=415,
            detail="Unsupported status media file type.",
        )

    return {
        "success": True,
        "platform": "WhatsApp Status",
        "file": str(file_path),
        "file_name": file_path.name,
        "message": "Status media found successfully.",
    }
