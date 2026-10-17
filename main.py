

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
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
                "enabled": False,
                "note": "Integration pending",
            },
            {
                "id": "instagram",
                "name": "Instagram",
                "enabled": False,
                "note": "Integration pending",
            },
            {
                "id": "facebook",
                "name": "Facebook",
                "enabled": False,
                "note": "Integration pending",
            },
            {
                "id": "pinterest",
                "name": "Pinterest",
                "enabled": False,
                "note": "Integration pending",
            },
            {
                "id": "snapchat",
                "name": "Snapchat",
                "enabled": False,
                "note": "Integration pending",
            },
            {
                "id": "chrome",
                "name": "Chrome / Direct Link",
                "enabled": False,
                "note": "Supported direct media links integration pending",
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
    
@app.get("/api/v1/instagram/profile")
def instagram_profile(username: str):
    import instaloader

    username = username.strip().lstrip("@")

    if not username or "/" in username or " " in username:
        raise HTTPException(
            status_code=400,
            detail="Please provide a valid Instagram username.",
        )

    try:
        loader = instaloader.Instaloader()
        profile = instaloader.Profile.from_username(
            loader.context,
            username,
        )

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
        raise HTTPException(
            status_code=400,
            detail="Instagram profile information could not be retrieved.",
        )

from pathlib import Path
from urllib.parse import urlparse
import requests


@app.get("/api/v1/instagram/dp")
def instagram_download_dp(username: str):
    import instaloader

    username = username.strip().lstrip("@")

    if (
        not username
        or len(username) > 30
        or not username.replace(".", "").replace("_", "").isalnum()
    ):
        raise HTTPException(
            status_code=400,
            detail="Please provide a valid Instagram username.",
        )

    try:
        loader = instaloader.Instaloader()
        profile = instaloader.Profile.from_username(
            loader.context, username
        )

        image_url = str(profile.profile_pic_url)
        host = urlparse(image_url).hostname or ""

        if not host.endswith(".cdninstagram.com"):
            raise HTTPException(
                status_code=400,
                detail="Unexpected profile picture URL.",
            )

        response = requests.get(
            image_url,
            timeout=20,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        response.raise_for_status()

        final_host = urlparse(response.url).hostname or ""
        if not final_host.endswith(".cdninstagram.com"):
            raise HTTPException(
                status_code=400,
                detail="Unexpected download destination.",
            )

        if not response.headers.get("Content-Type", "").startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail="Instagram did not return an image.",
            )

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
        raise HTTPException(
            status_code=400,
            detail="Public Instagram DP download failed. Try again later.",
        )
