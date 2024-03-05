# https://github.com/arrrlo/Google-Images-Search

from os import environ as env

from google_images_search import GoogleImagesSearch


class ImageSearchEngine:
    def __init__(self, api_key: str = None, cx: str = None, size: str = 'large', kind: str = 'png', top_n: int = 20):
        if api_key is None:
            api_key = env.get('RR_GIS_API_KEY')

            if api_key is None:
                raise ValueError('Google Image Search api key is required')

        if cx is None:
            cx = env.get('RR_GIS_CX')

            if cx is None:
                raise ValueError('Google Image Search context is required')

        self.api_key = api_key
        self.cx = cx

        self.size = size
        self.kind = kind
        self.top_n = top_n

    def search(self, query: str):
        gis = GoogleImagesSearch(self.api_key, self.cx)

        search_params = {
            'q': query,
            'num': self.top_n,
            'fileType': (kind := self.kind),
            'safe': 'medium',
            'imgType': 'photo',
            'imgSize': self.size
        }

        gis.search(search_params)

        urls = []

        for image in gis.results():
            url = image.url

            if not url.startswith('https://preview.redd.it') and url.endswith(kind):
                urls.append(image.url)

        if len(urls) > 0:
            return urls

        raise ValueError(f'Can\'t find an image for query \'{query}\'')
