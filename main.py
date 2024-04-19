import YouTubeSearch as youtube

def main():
    _youtube = youtube.YouTubeSearch('YOUR_CLIENT_SECRET_FILE.json', 'UC7f5bVxWsm3jlZIPDzOMcAg')
    results = _youtube.get_videos_from_channel(2, '2022-01-01T17:47:00Z')
    for result in results:
        print(result)
    print(_youtube.get_channel_name('UC7f5bVxWsm3jlZIPDzOMcAg'))
    test = _youtube.get_channel_id('1Craft')
    print(_youtube.get_channel_url(test))


if __name__ == "__main__":
    main()