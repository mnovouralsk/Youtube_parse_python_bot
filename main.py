import os

import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors

import YouTubeSearch as youtube

def main():
    _youtube = youtube.YouTubeSearch('YOUR_CLIENT_SECRET_FILE.json', 'UC7f5bVxWsm3jlZIPDzOMcAg')
    _youtube.get_videos_from_channel()



if __name__ == "__main__":
    main()