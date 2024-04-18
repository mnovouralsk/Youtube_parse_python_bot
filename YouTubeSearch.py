import os

import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors

class YouTubeSearch:

    def __init__(self, client_secrets_file, channel_id):
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
        self.scopes = ["https://www.googleapis.com/auth/youtube.force-ssl"]

        self.api_service_name = "youtube"
        self.api_version = "v3"
        self.channel_id = channel_id
        self.client_secrets_file = client_secrets_file
        self.base_video_url = 'https://www.youtube.com/watch?v='
        self.next_page_token = ''

        # Get credentials and create an API client
        self.flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(self.client_secrets_file, self.scopes)
        self.credentials = self.flow.run_console()
        self.youtube = googleapiclient.discovery.build(self.api_service_name, self.api_version, credentials=self.credentials)

    def get_videos_from_channel(self):
        next_page_token = ''
        while True:
            request = self.youtube.search().list(
                channelId = self.channel_id,
                part = "snippet",
                order = 'date',
                publishedAfter = '2024-01-01T17:47:00Z',
                maxResults = 5,
                pageToken = next_page_token
            )
            response = request.execute()

            for i in response['items']:
                if i['id']['kind'] == "youtube#video":
                    print(self.base_video_url + i['id']['videoId'] + '    ' + i['snippet']['publishedAt'] + '    ' + i['snippet']['title'])
            try:
                next_page_token = response['nextPageToken']
            except:
                break
        #print(response)

        return True