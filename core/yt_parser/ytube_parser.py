# core/yt_parser/ytube_parser.py
import os
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle

from core.logger import logger
from core.yt_parser.video_storage import load_json, save_json
from config import Config

# Конфигурация
config = Config()
YOUTUBE_API_KEY = config.youtube_api_key
YOUR_CLIENT_SECRET_FILE = config.youtube_secret_file
TOKEN_FILE = config.token_file
USE_OAUTH = config.use_oauth

START_DATE = datetime.fromisoformat(config.start_date).replace(tzinfo=timezone.utc)

CHANNELS_JSON = config.channels_json
LAST_VIDEO_JSON = config.last_video_json


class YouTubeParser:
    """Класс для работы с YouTube API и поиска новых видео на каналах."""

    def __init__(self):
        os.makedirs("data", exist_ok=True)

        self.youtube = self._get_youtube_service()
        self.channels = self._load_channels()
        self.last_videos = self._load_last_videos()

    # -------------------- YouTube сервис --------------------
    def _get_youtube_service(self):
        """Инициализация клиента YouTube API"""
        if USE_OAUTH:
            logger.info("Используется OAuth авторизация YouTube API...")
            return self._get_youtube_service_oauth()
        else:
            logger.info("Используется API Key авторизация YouTube API...")
            return build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

    def _get_youtube_service_oauth(self):
        """OAuth авторизация через client_secret.json"""
        scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
        creds = None

        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "rb") as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(YOUR_CLIENT_SECRET_FILE, scopes)
                creds = flow.run_local_server(port=0)
            with open(TOKEN_FILE, "wb") as token:
                pickle.dump(creds, token)

        return build("youtube", "v3", credentials=creds)

    # -------------------- Каналы и видео --------------------
    def _load_channels(self) -> List[str]:
        """Загрузка списка каналов из JSON"""
        if not os.path.exists(CHANNELS_JSON):
            logger.error(f"Файл с каналами не найден: {CHANNELS_JSON}")
            return []
        with open(CHANNELS_JSON, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_last_videos(self) -> Dict[str, str]:
        """Загрузка последних videoId по каналам"""
        if os.path.exists(LAST_VIDEO_JSON):
            with open(LAST_VIDEO_JSON, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_last_videos(self):
        """Сохранение последних videoId"""
        save_json(LAST_VIDEO_JSON, self.last_videos)

    # -------------------- Получение видео --------------------
    def fetch_latest_video(self, channel_id: str) -> Optional[Dict]:
        """Получение последнего видео на канале"""
        try:
            request = self.youtube.search().list(
                part="snippet",
                channelId=channel_id,
                maxResults=1,
                order="date",
                type="video",
            )
            response = request.execute()

            if not response.get("items"):
                return None

            video = response["items"][0]
            video_id = video["id"]["videoId"]
            snippet = video["snippet"]

            return {
                "channel_id": channel_id,
                "video_id": video_id,
                "title": snippet["title"],
                "description": snippet.get("description", ""),
                "published_at": snippet["publishedAt"],
                "thumbnail": snippet["thumbnails"]["high"]["url"],
                "url": f"https://www.youtube.com/watch?v={video_id}",
            }

        except Exception as e:
            logger.error(f"Ошибка при получении видео с канала {channel_id}: {e}")
            return None

    # -------------------- Основная проверка --------------------
    def check_for_new_videos(self) -> List[Dict]:
        """
        Проверка всех каналов на наличие новых видео с учетом START_DATE.
        Возвращает список новых видео.
        """
        logger.info("🔍 Проверка новых видео на каналах...")

        new_videos = []

        for channel in self.channels:  # channel — dict
            channel_id = channel["id"]  # строка
            logger.info(f"Проверяем канал: {channel_id}")

            last_known_video = self.last_videos.get(channel_id)
            published_after = START_DATE.isoformat() if not last_known_video else None

            videos = self._get_channel_videos(channel_id, published_after)

            for video in videos:
                video_id = video["id"]["videoId"]
                snippet = video["snippet"]

                # Пропускаем уже известные видео
                if last_known_video and video_id == last_known_video:
                    break

                new_videos.append({
                    "channel_id": channel_id,
                    "video_id": video_id,
                    "title": snippet["title"],
                    "description": snippet.get("description", ""),
                    "thumbnail": snippet["thumbnails"]["high"]["url"],
                    "published_at": snippet["publishedAt"],
                    "url": f"https://www.youtube.com/watch?v={video_id}"
                })

            if videos:
                self.last_videos[channel_id] = videos[0]["id"]["videoId"]

        self._save_last_videos()
        logger.info(f"✅ Найдено {len(new_videos)} новых видео")
        return new_videos

    def _get_channel_videos(self, channel_id: str, published_after: Optional[str] = None) -> List[Dict]:
        """Получение всех видео канала с возможностью фильтрации по дате"""
        try:
            request = self.youtube.search().list(
                part="snippet",
                channelId=channel_id,
                maxResults=5,  # можно увеличить, если нужно
                order="date",
                type="video",
                publishedAfter=published_after
            )
            response = request.execute()
            return response.get("items", [])
        except Exception as e:
            logger.error(f"Ошибка получения видео с канала {channel_id}: {e}")
            return []

# -------------------- Тестирование --------------------
# if __name__ == "__main__":
#     parser = YouTubeParser()
#     new_videos = parser.check_for_new_videos()
#     for v in new_videos:
#         print(f"{v['title']} → {v['url']}")
