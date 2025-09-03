# YouTube_parse_python_bot: Автоматизация За гранью

> Добро пожаловать. Это не просто бот. Это инструмент. Для тех, кто видит больше, чем просто видео. Для тех, кто ищет. И находит.

---

### 📦 Возможности

Мы собрали это, чтобы ты мог быстро проникнуть в суть.

* **Сканирование:** Ищи видео по ключевым словам. Не просто слова, а цели.
* **Сбор данных:** ID, название, описание. Ничего лишнего, только факты.
* **Очистка:** Отсеиваем дубликаты. Только уникальные результаты. Истина одна.
* **Подключение:** Мы используем YouTube API через OAuth 2.0. Это наш доступ к системе.
* **Маскировка:** Код живёт в отдельной ветке. Никто не узнает, пока ты не сольёшь его в `main`.

---

### ⚙️ Установка

В мире, где всё контролируется, ты должен следовать инструкциям.

1.  **Клонирование:**
    ```bash
    git clone [https://github.com/mnovouralsk/Youtube_parse_python_bot.git](https://github.com/mnovouralsk/Youtube_parse_python_bot.git)
    cd Youtube_parse_python_bot
    ```
2.  **Изоляция:**
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # Linux/macOS
    source venv/bin/activate
    ```
3.  **Зависимости:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Доступ:**
    * Получи `client_secret.json` с Google Cloud Console. Это твой ключ.
    * Положи его в корень проекта.

---

### 🚀 Использование

Вот как это работает. Запусти это и наблюдай.

```python
from YouTubeSearch import YouTubeSearch

# Инициализация
YTube = YouTubeSearch('YOUR_CLIENT_SECRET_FILE.json')

# Поиск
key_words = "Python programming"
formatted_datetime = "2025-09-03T00:00:00Z"

results = YTube.search_videos(count=30, keywords=key_words, date=formatted_datetime)

# Отсев
unique_results = {}
for video_id, title, description in results:
    if video_id not in unique_results:
        unique_results[video_id] = (title, description)

unique_results_list = [
    (video_id, title, description)  
    for video_id, (title, description) in unique_results.items()
]
```

### 📂 Структура
```bash
Youtube_parse_python_bot/
│
├── YouTubeSearch.py         # Мозг
├── main.py                  # Точка входа в систему
├── requirements.txt         # Зависимости
└── README.md
```

### ⚠️ Важные моменты

- Для аутентификации используй flow.run_local_server(). Старые методы уже не работают.

### 🔗 Полезные ссылки
[Google YouTube API](https://developers.google.com/youtube/v3)
