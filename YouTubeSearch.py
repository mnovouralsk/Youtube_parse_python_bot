# Этот код написан на языке Python и представляет класс YouTubeSearch, который используется для выполнения поиска видео и информации о каналах на YouTube.

import os

import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors

scopes = ["https://www.googleapis.com/auth/youtube.force-ssl"]

class YouTubeSearch:

    def __init__(self, client_secrets_file):
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        self.api_service_name = "youtube"
        self.api_version = "v3"
        self.client_secrets_file = client_secrets_file
        self.base_video_url = 'https://www.youtube.com/watch?v='
        self.base_channel_url = 'https://www.youtube.com/channel/'
        self.next_page_token = ''
        self.authenticate()

    def authenticate(self):
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(self.client_secrets_file, scopes)
        credentials = flow.run_console()
        self.youtube = googleapiclient.discovery.build(self.api_service_name, self.api_version, credentials=credentials)

    def get_videos_from_channel(self, count=5, date='2024-01-01T17:47:00Z', channel_id=''):
        results = []
        self.channel_id = channel_id

        if (count > 50):
            stage = (count // 50) + 1
            _count = 50
        else:
            stage = 1
            _count = count

        while stage > 0:
            stage -= 1

            request = self.youtube.search().list(
                channelId = self.channel_id,
                part = "snippet",
                order = 'date',
                publishedAfter = date,
                maxResults = _count,
                pageToken = self.next_page_token
            )
            response = request.execute()

            for i in response['items']:
                if i['id']['kind'] == "youtube#video":
                    results.append((i['id']['videoId'], i['snippet']['publishedAt'], i['snippet']['title']))
                    # print(self.base_video_url + i['id']['videoId'] + '    ' + i['snippet']['publishedAt'] + '    ' + i['snippet']['title'])
            try:
                self.next_page_token = response['nextPageToken']
            except:
                break
            _count = _count - 50 * stage
        self.next_page_token = ''
        return tuple(results)

    # получение id канала
    def get_channel_id(self, channel_name):
        request = self.youtube.channels().list(
            part = "snippet",
            forUsername = channel_name
        )
        response = request.execute()
        return response['items'][0]['id']

    # получение названия канала
    def get_channel_name(self, channel_id):
        request = self.youtube.channels().list(
            part = "snippet",
            id = channel_id
        )
        response = request.execute()
        return response['items'][0]['snippet']['title']

    # получение описания канала
    def get_channel_description(self, channel_id):
        request = self.youtube.channels().list(
            part = "snippet",
            id = channel_id
        )
        response = request.execute()
        return response['items'][0]['snippet']['description']

    # получение изображения канала
    def get_channel_thumbnail(self, channel_id):
        request = self.youtube.channels().list(
            part = "snippet",
            id = channel_id
        )
        response = request.execute()
        return response['items'][0]['snippet']['thumbnails']['high']['url']

    # получение количества подписчиков
    def get_channel_subscribers(self, channel_id):
        request = self.youtube.channels().list(
            part = "statistics",
            id = channel_id
        )
        response = request.execute()
        return response['items'][0]['statistics']['subscriberCount']

    # получение количества просмотров
    def get_channel_view_count(self, channel_id):
        request = self.youtube.channels().list(
            part = "statistics",
            id = channel_id
        )
        response = request.execute()
        return response['items'][0]['statistics']['viewCount']

    # получение количества видео
    def get_channel_video_count(self, channel_id):
        request = self.youtube.channels().list(
            part = "statistics",
            id = channel_id
        )
        response = request.execute()
        return response['items'][0]['statistics']['videoCount']

    # получение ссылки на видео
    def get_video_url(self, video_id):
        return self.base_video_url + video_id

    # получение ссылки на канал
    def get_channel_url(self, channel_id):
        return self.base_channel_url + channel_id

    def search_videos(self, count=1, keywords='', date='2024-01-01T17:47:00Z'):
        results = []

        if (count > 50):
            stage = (count // 50) + 1
            _count = 50
        else:
            stage = 1
            _count = count

        while stage > 0:
            stage -= 1

            request = self.youtube.search().list(
                q = keywords,
                part = "snippet",
                type = "video",
                order = 'relevance',
                publishedAfter = date,
                maxResults = _count,
                pageToken = self.next_page_token
            )
            response = request.execute()

            for i in response['items']:
                if i['id']['kind'] == "youtube#video":
                    results.append((i['id']['videoId'], i['snippet']['title'], i['snippet']['description']))
                    # print(i)
            try:
                self.next_page_token = response['nextPageToken']
            except:
                break
            _count = _count - 50 * stage
        self.next_page_token = ''
        return tuple(results)