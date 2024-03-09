# https://github.com/arrrlo/Google-Images-Search

from os import environ as env

from google_images_search import GoogleImagesSearch
from googleapiclient.errors import HttpError

from .util import normalize


class ImageSearchEngine:
    def __init__(self, api_key: str = None, api_key_fallback: str = None, cx: str = None, size: str = 'large', kind: str = 'png', top_n: int = 20):
        if api_key is None:
            api_key = env.get('RR_GIS_API_KEY')

            if api_key is None:
                raise ValueError('Google Image Search api key is required')

        if api_key_fallback is None:
            api_key_fallback = env.get('RR_GIS_API_KEY_FALLBACK')

            if api_key_fallback is None:
                raise ValueError('Google Image Search fallback api key is required')

        if cx is None:
            cx = env.get('RR_GIS_CX')

            if cx is None:
                raise ValueError('Google Image Search context is required')

        self.api_key = api_key
        self.api_key_fallback = api_key_fallback
        self.cx = cx

        self.size = size
        self.kind = kind
        self.top_n = top_n

        self.gis = GoogleImagesSearch(self.api_key, self.cx)

    def search(self, query: str, root_query: str = None):
        search_params = {
            'q': query,
            'num': self.top_n,
            'fileType': (kind := self.kind),
            'safe': 'medium',
            'imgType': 'photo',
            'imgSize': self.size
        }

        gis = self.gis

        try:
            gis.search(search_params)
        except HttpError:
            self.gis = gis = GoogleImagesSearch(self.api_key_fallback, self.cx)
            gis.search(search_params)

        urls = []

        for image in self.gis.results():
            url = image.url

            if not url.startswith('https://preview.redd.it') and url.endswith(kind):
                urls.append(image.url)

        if len(urls) > 0:
            return urls

        truncated_query = ' '.join(normalize(query).split(' ')[:-1])

        if len(truncated_query) > 0:
            return self.search(truncated_query, root_query = query if root_query is None else root_query)

        raise ValueError(f'Can\'t find an image for query \'{query if root_query is None else root_query}\'')
