import json
from config import Config
from core.logger import logger


config = Config()
LAST_VIDEO_JSON = config.last_video_json
PENDING_POSTS_JSON = config.pending_posts_json

def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.info(f"{path} не найден, создаю новый.")
        return {}
    except Exception as e:
        logger.error(f"Ошибка загрузки {path}: {e}")
        return {}

def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения {path}: {e}")
