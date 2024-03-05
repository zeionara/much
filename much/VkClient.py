from pathlib import Path
from os import environ as env
from io import BytesIO, BufferedReader

from requests import post as postt, get

from .ImageSearchEngine import ImageSearchEngine


TIMEOUT = 3600


def make_attachments(audio: int, media_owner: int, poster: int):
    return f"audio{media_owner}_{audio},photo{media_owner}_{poster}"


class VkClient:
    def __init__(
        self, post_token: str = None, audio_token: str = None,
        post_owner: int = None, audio_owner: int = None,
        post_album: int = None,
        api_version: str = '5.199'
    ):
        if post_token is None:
            post_token = env.get('MUCH_VK_POST_TOKEN')

            if post_token is None:
                raise ValueError('vk token in required to post content')

        if post_owner is None:
            post_owner = env.get('MUCH_VK_POST_OWNER')

            if post_owner is None:
                raise ValueError('vk owner is required to post content')

            post_owner = int(post_owner)

        if post_album is None:
            post_album = env.get('MUCH_VK_POST_ALBUM')

            if post_album is None:
                raise ValueError('vk album id is required to post content')

            post_album = int(post_album)

        if audio_token is None:
            audio_token = env.get('MUCH_VK_AUDIO_TOKEN')

            if audio_token is None:
                raise ValueError('vk token in required to upload audio')

        if audio_owner is None:
            audio_owner = env.get('MUCH_VK_AUDIO_OWNER')

            if audio_owner is None:
                raise ValueError('vk owner is required to upload audio')

            audio_owner = int(audio_owner)

        self.post_token = post_token
        self.post_owner = post_owner
        self.post_album = post_album

        self.audio_token = audio_token
        self.audio_owner = audio_owner

        self.api_version = api_version

    def post(self, path: str, title: str, caption: str, artist: str = None, message: str = None):
        # print('Uploading audio...')
        audio = self._upload_audio(path, title, artist)
        # print(f'Uploaded audio {audio}, creating post...')
        return self._post(caption, audio, message)
        # print(f'Created post {post_id}')

        # return post_id

    def _upload_audio(self, path: str, title: str, artist: str = None):
        token = self.audio_token
        token_owner = self.audio_owner
        audio_owner = self.post_owner

        api_version = self.api_version

        response = postt(
            url = 'https://api.vk.com/method/audio.getUploadServer',
            data = {
                'access_token': token,
                'v': api_version
            },
            timeout = TIMEOUT
        )

        if response.status_code == 200:
            upload_url = response.json()['response']['upload_url']

            with open(path, 'rb') as file:
                response = postt(
                    url = upload_url,
                    files = {
                        'file': (path, file)
                    },
                    timeout = TIMEOUT
                )

            if response.status_code == 200:
                response_json = response.json()

                audio = response_json['audio']
                server = response_json['server']
                hash_ = response_json['hash']

                response = postt(
                    url = 'https://api.vk.com/method/audio.save',
                    data = {
                        'access_token': token,
                        'audio': audio,
                        'server': server,
                        'hash': hash_,
                        'v': api_version,
                        'artist': artist,
                        'title': title
                    },
                    timeout = TIMEOUT
                )

                if response.status_code == 200:
                    response_json = response.json()['response']

                    if audio_owner is not None and token_owner != audio_owner:
                        response = postt(
                            url = 'https://api.vk.com/method/audio.add',
                            data = {
                                'access_token': token,
                                'audio_id': (audio_id := response_json['id']),
                                'owner_id': (owner_id := response_json['owner_id']),
                                'group_id': abs(audio_owner),
                                'v': api_version
                            },
                            timeout = TIMEOUT
                        )

                        if response.status_code == 200:
                            final_audio_id = response.json().get('response')

                            response = postt(
                                url = 'https://api.vk.com/method/audio.delete',
                                data = {
                                    'audio_id': audio_id,
                                    'owner_id': owner_id,
                                    'access_token': token,
                                    'v': api_version
                                },
                                timeout = TIMEOUT
                            )

                            if response.status_code == 200:
                                # print(response.json())
                                return final_audio_id
                            raise ValueError(f'Unexpected response from server when deleting audio from the user\'s list: {response.content}')
                        raise ValueError(f'Unexpected response from server when adding audio to the group: {response.content}')
                raise ValueError(f'Unexpected response from server when saving uploaded audio: {response.content} {response.status_code}')
            raise ValueError(f'Unexpected response from server when uploading audio: {response.content}')
        raise ValueError(f'Unexpected response from server when obtaining upload url: {response.content}')

    def _post(self, caption: str, audio: int, title: str = None):
        owner = self.post_owner
        album = self.post_album
        token = self.post_token

        api_version = self.api_version

        response = postt(
            url = 'https://api.vk.com/method/photos.getUploadServer',
            data = {
                'group_id': abs(owner),
                'album_id': album,
                'access_token': token,
                'v': api_version
            },
            timeout = TIMEOUT
        )

        if response.status_code == 200:
            response_json = response.json()['response']

            upload_url = response_json['upload_url']

            link = ImageSearchEngine().search(caption)

            response = postt(
                url = upload_url,
                files = {
                    'file': (Path(link).name, BufferedReader(BytesIO(get(link, timeout = TIMEOUT).content)))
                },
                timeout = TIMEOUT
            )

            if response.status_code == 200:
                response_json = response.json()

                photos_list = response_json['photos_list']
                server = response_json['server']
                hash_ = response_json['hash']

                response = postt(
                    url = 'https://api.vk.com/method/photos.save',
                    data = {
                        'group_id': abs(owner),
                        'album_id': album,
                        'server': server,
                        'photos_list': photos_list,
                        'hash': hash_,
                        'caption': caption,
                        'access_token': token,
                        'v': api_version
                    },
                    timeout = TIMEOUT
                )

                if response.status_code == 200:
                    try:
                        response_json = response.json()['response']
                    except KeyError:
                        raise ValueError(f'Invalid response after saving photos: {response.json()}')

                    photo_id = response_json[0]['id']

                    response = postt(
                        url = 'https://api.vk.com/method/wall.post',
                        data = {
                            'owner_id': owner,
                            'from_group': 1,
                            'message': title,
                            'attachments': make_attachments(audio, owner, photo_id),
                            'access_token': token,
                            'v': api_version
                        },
                        timeout = TIMEOUT
                    )

                    if response.status_code == 200:
                        return response.json()['response']['post_id']

                    raise ValueError(f'Unexpected response from server when creating a post: {response.content}')
                raise ValueError(f'Unexpected response from server when saving uploaded photo: {response.content}')
            raise ValueError(f'Unexpected response from server when uploading photo: {response.content}')
        raise ValueError(f'Unexpected response from server when obtaining upload url: {response.content}')