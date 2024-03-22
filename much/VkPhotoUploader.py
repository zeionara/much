from pathlib import Path
from os import environ as env
from io import BytesIO, BufferedReader

from requests import post, get

from rr.util import is_url

from .VkUploader import VkUploader, URL_TEMPLATE, TIMEOUT, API_VERSION


class VkPhotoUploader(VkUploader):
    def __init__(
        self,
        token: str,
        owner: int,
        album: int,
        api_version: str = API_VERSION
    ):
        self.token = token
        self.owner = owner
        self.album = album
        self.api_version = api_version

    def _get_upload_server(self):
        response = post(
            URL_TEMPLATE.format(method = 'photos.getUploadServer'),
            data = {
                'group_id': self.owner,
                'album_id': self.album,
                'access_token': self.token,
                'v': self.api_version
            },
            timeout = TIMEOUT
        )

        body = self._validate_response('Can\'t get url for uploading photo', response, validate = lambda body: 'response' in body and 'upload_url' in body['response'])

        return body['response']['upload_url']

    def _upload(self, url: str, path: str):
        def get_response(file):
            return post(
                url,
                files = {
                    'file': file
                },
                timeout = TIMEOUT
            )

        if is_url(path):
            file = (f'image{Path(path).suffix}', BufferedReader(BytesIO(get(path, timeout = TIMEOUT).content)))
            response = get_response(file)
        else:
            with open(path, 'rb') as file:
                response = get_response(file)

        body = self._validate_response('Can\'t upload photo', response, validate = lambda body: 'photos_list' in body and 'server' in body and 'hash' in body and len(body['photos_list']) > 0)

        return body['photos_list'], body['server'], body['hash']

    def _save(self, photos_list, server, hash_, caption: str = None):
        response = post(
            URL_TEMPLATE.format(method = 'photos.save'),
            data = {
                'group_id': self.owner,
                'album_id': self.album,
                'server': server,
                'photos_list': photos_list,
                'hash': hash_,
                'caption': caption[:2048],
                'access_token': self.token,
                'v': self.api_version
            },
            timeout = TIMEOUT
        )

        body = self._validate_response(
            'Can\'t save uploaded photo',
            response,
            validate = lambda body: 'response' in body and isinstance(body['response'], list) and len(body['response']) > 0
        )

        photo = body['response'][0]

        return photo['sizes'][-1]['url'], photo['id'], photo['owner_id']

    def upload(self, path: str, caption: str, verbose: bool = False):
        if verbose:
            print('Getting upload url...')

        url = self._get_upload_server()

        if verbose:
            print('Got upload url. Uploading photo...')

        photos_list, server, hash_ = self._upload(url, path)

        if verbose:
            print(f'Uploaded to {url}. Saving uploaded photo...')

        url, photo_id, _ = self._save(photos_list, server, hash_, caption)

        if verbose:
            print(f'Uploaded as {url}')

        return photo_id

    @classmethod
    def make(cls):
        token = env.get('MUCH_VK_POST_TOKEN')

        if token is None:
            raise ValueError('vk token in required to upload files')

        owner = env.get('MUCH_VK_POST_OWNER')

        if owner is None:
            raise ValueError('vk post owner is required to post content')

        album = env.get('MUCH_VK_POST_ALBUM')

        if album is None:
            raise ValueError('vk album is required to post content')

        return cls(token, abs(int(owner)), int(album))
