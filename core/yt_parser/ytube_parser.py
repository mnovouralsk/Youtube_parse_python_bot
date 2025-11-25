# core/yt_parser/ytube_parser.py
import os
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle

from core.logger import logger
from core.yt_parser.video_storage import load_json, save_json
from config import Config

config = Config()

YOUTUBE_API_KEY = config.youtube_api_key
YOUR_CLIENT_SECRET_FILE = config.youtube_secret_file
TOKEN_FILE = config.token_file
USE_OAUTH = config.use_oauth

START_DATE = datetime.fromisoformat(config.start_date).replace(tzinfo=timezone.utc)
START_DAY_BEGIN = START_DATE.replace(hour=0, minute=0, second=0, microsecond=0)
START_DAY_END = START_DATE.replace(hour=23, minute=59, second=59, microsecond=999999)

CHANNELS_JSON = config.channels_json
LAST_VIDEO_JSON = config.last_video_json
DELETED_VIDS_JSON = getattr(config, "deleted_videos_json", "deleted_videos.json")


# ---------------------- Utility functions ----------------------
def load_deleted_list() -> List[str]:
    """Load deleted videoId list."""
    if not os.path.exists(DELETED_VIDS_JSON):
        save_json(DELETED_VIDS_JSON, {"deleted": []})
        return []
    data = load_json(DELETED_VIDS_JSON)
    if not isinstance(data, dict) or "deleted" not in data:
        save_json(DELETED_VIDS_JSON, {"deleted": []})
        return []
    return data["deleted"]


def parse_yt_datetime(dt: str) -> datetime:
    """Convert YouTube `publishedAt` ISO string to timezone-aware UTC datetime."""
    try:
        # Пытаемся распарсить дату
        return datetime.fromisoformat(dt.replace("Z", "+00:00"))
    except Exception as e:
        logger.error(f"Ошибка обработки YouTube datetime string '{dt}': {e}")

        # Возвращаем "безопасное" значение, которое гарантированно будет отфильтровано
        # (дата за 5 дней до начала целевого дня)
        return START_DAY_BEGIN - timedelta(days=5)


# ---------------------- Main Parser Class ----------------------
class YouTubeParser:
    """YouTube daily-range parser with filtering by deleted list."""

    def __init__(self):
        os.makedirs("data", exist_ok=True)

        self.youtube = self._get_youtube_service()
        self.channels = self._load_channels()
        self.last_videos = self._load_last_videos()
        self.deleted_videos = load_deleted_list()

    # ----------- API Init -----------

    def _get_youtube_service(self):
        if USE_OAUTH:
            logger.info("Using OAuth YouTube authentication...")
            return self._get_youtube_service_oauth()
        else:
            logger.info("Using API Key YouTube authentication...")
            return build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

    def _get_youtube_service_oauth(self):
        scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
        creds = None

        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "rb") as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception:
                    creds = None

            if not creds:
                flow = InstalledAppFlow.from_client_secrets_file(
                    YOUR_CLIENT_SECRET_FILE, scopes
                )
                creds = flow.run_local_server(port=0)

            with open(TOKEN_FILE, "wb") as token:
                pickle.dump(creds, token)

        return build("youtube", "v3", credentials=creds)

    # ----------- Loaders -----------

    def _load_channels(self) -> List[Dict]:
        if not os.path.exists(CHANNELS_JSON):
            logger.error(f"Channels JSON not found: {CHANNELS_JSON}")
            return []
        with open(CHANNELS_JSON, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_last_videos(self) -> Dict[str, str]:
        if os.path.exists(LAST_VIDEO_JSON):
            with open(LAST_VIDEO_JSON, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_last_videos(self):
        save_json(LAST_VIDEO_JSON, self.last_videos)

    # ----------- API Requests -----------

    def _get_uploads_playlist_id(self, channel_id: str) -> str | None:
        try:
            request = self.youtube.channels().list(part="contentDetails", id=channel_id)
            response = request.execute()
            return response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        except Exception as e:
            logger.error(f"Ошибка получения плейлиста загрузок для {channel_id}: {e}")
            return None

    def _get_channel_videos_paged(self, channel_id: str) -> List[Dict]:
        playlist_id = self._get_uploads_playlist_id(channel_id)
        if not playlist_id:
            return []

        all_raw_videos = []
        next_page_token = None

        while True:
            try:
                request = self.youtube.playlistItems().list(
                    part="snippet",
                    playlistId=playlist_id,
                    maxResults=50,
                    pageToken=next_page_token,
                )
                response = request.execute()

                # --- Логика остановки ---
                for item in response.get("items", []):
                    pub_date = parse_yt_datetime(item["snippet"]["publishedAt"])

                    # Если видео опубликовано ДО начала нашего дня, то все последующие (более старые)
                    # видео нам тоже не нужны. Завершаем цикл.
                    if pub_date < START_DAY_BEGIN:
                        logger.info(
                            f"Остановка: достигнуто видео от {pub_date.date()}, более старое, чем {START_DAY_BEGIN.date()}"
                        )
                        return all_raw_videos

                    # Если видео находится в целевом диапазоне (или позже, что маловероятно для отсортированного списка)
                    all_raw_videos.append(item)

                next_page_token = response.get("nextPageToken")
                if not next_page_token:
                    break

            except Exception as e:
                logger.error(
                    f"Ошибка загрузки видео из плейлиста {playlist_id} канала {channel_id}: {e}"
                )
                break

        return all_raw_videos

    # ----------- Main Logic -----------

    def check_for_new_videos(self) -> List[Dict]:
        """
        Returns ONLY videos published on START_DATE between 00:00–23:59:59 UTC,
        excluding deleted ones and previously processed ones.
        """
        logger.info(
            f"🔍 Checking for videos published on {START_DATE.date()} "
            f"from {START_DAY_BEGIN} to {START_DAY_END}"
        )

        new_videos = []

        for channel in self.channels:
            channel_id = channel["id"]
            channel_name = channel["name"]
            logger.info(f"Checking channel: {channel_id} ({channel_name})")

            videos = self._get_channel_videos_paged(channel_id)

            # Сортируем (если API не гарантирует порядок)
            videos.sort(key=lambda x: x["snippet"]["publishedAt"], reverse=True)
            found_videos_for_channel = []

            for video in videos:
                vid = video["snippet"]["resourceId"]["videoId"]

                # Skip deleted
                if vid in self.deleted_videos:
                    continue

                # Skip already processed
                if vid == self.last_videos.get(channel_id):
                    continue

                snippet = video["snippet"]
                pub = parse_yt_datetime(snippet["publishedAt"])

                if not (START_DAY_BEGIN <= pub <= START_DAY_END):
                    continue

                video_data = {
                    "channel_id": channel_id,
                    "channel_name": channel_name,
                    "video_id": vid,
                    "title": snippet["title"],
                    "description": snippet.get("description", ""),
                    "thumbnail": snippet["thumbnails"]["high"]["url"],
                    "published_at": snippet["publishedAt"],
                    "url": f"https://www.youtube.com/watch?v={vid}",
                }

                new_videos.append(video_data)
                found_videos_for_channel.append(video_data)

            if found_videos_for_channel:
                # Так как список отсортирован по дате (newest-first), элемент [0] — это самый новый
                self.last_videos[channel_id] = found_videos_for_channel[0]["video_id"]

        self._save_last_videos()
        logger.info(f"✅ Found {len(new_videos)} videos matching date filter.")

        return new_videos
