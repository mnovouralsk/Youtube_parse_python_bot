import YouTubeSearch as youtube
# from YouTubeSearch import quality
from config import BOT_TOKEN
from datetime import datetime, timedelta, timezone
from typing import List, Tuple

import telebot
import json
import os
import time

def main():
    key_words = 'python'

    bot = telebot.TeleBot(BOT_TOKEN)
    YTube = youtube.YouTubeSearch('YOUR_CLIENT_SECRET_FILE.json')
    # Получение текущей даты и времени
    current_datetime = datetime.now(timezone.utc)

    # Вычитание 3 часов
    adjusted_datetime = current_datetime - timedelta(hours=48)

    # Преобразование откорректированной даты и времени в нужный формат
    formatted_datetime = adjusted_datetime.strftime('%Y-%m-%d') + 'T' + adjusted_datetime.strftime('%H:%M:%S') + 'Z'

    # while True:
    results: List[Tuple[str, str, str]] = YTube.search_videos(
        count=30,
        keywords=key_words,
        date=formatted_datetime
    ) or []

    unique_results = {}
    for video_id, title, description in results:
        if video_id not in unique_results:
            unique_results[video_id] = (title, description)

    # Преобразуем словарь обратно в список
    unique_results_list = [(video_id, title, description) for video_id, (title, description) in unique_results.items()]

    file_path = 'data.json'

    if os.path.exists(file_path):
        with open('data.json', 'r') as file:
            data = json.load(file)
    else:
        data = []

    if not isinstance(data, list):
        data = list(data)
        YTube.get_url_image_from_video('video_id', "default")

    # Преобразование элементов в кортежи
    data_tuples = [tuple(item) for item in data]
    unique_results_tuples = [tuple(item) for item in unique_results_list]


    # Создаем новый список, исключая элементы 2 и 3
    filtered_list = [x for x in unique_results_tuples if x not in data_tuples]

    for result in filtered_list:
        bot.send_message('1675247184', YTube.get_video_url(result[0]))
        print(result)
        time.sleep(0.9)

    # Очищаем файл
    if data != []:
        with open('data.json', 'w') as file:
            file.write('')

        # Сохраняем unique_results_list в файл
        with open('data.json', 'w') as file:
            json.dump(filtered_list, file)


if __name__ == "__main__":
    main()
