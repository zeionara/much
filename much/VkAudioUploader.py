from requests import post
from os import environ as env

# from rr.util import retry

from .VkUploader import VkUploader, URL_TEMPLATE, TIMEOUT, API_VERSION


class VkAudioUploader(VkUploader):
    def __init__(
        self,
        token: str,
        token_owner: int,
        audio_owner: int,
        playlist: int,
        community_token: str,
        playlist_token: str,
        playlist_owner: int,
        api_version: str = API_VERSION
    ):
        self.token = token
        self.token_owner = token_owner
        self.audio_owner = audio_owner
        self.api_version = api_version
        self.playlist = playlist
        self.playlist_token = playlist_token
        self.playlist_owner = playlist_owner
        self.community_token = community_token

    # @retry(times = 3)
    def _get_upload_server(self):
        response = post(
            URL_TEMPLATE.format(method = 'audio.getUploadServer'),
            data = {
                'access_token': self.token,
                'v': self.api_version
            },
            timeout = TIMEOUT
        )

        body = self._validate_response('Can\'t get upload url', response, validate = lambda body: 'response' in body and 'upload_url' in body['response'])

        return body['response']['upload_url']

    # @retry(times = 3)
    def _upload(self, url: str, path: str):
        with open(path, 'rb') as file:
            response = post(
                url,
                files = {
                    'file': (path, file)
                },
                timeout = TIMEOUT
            )

        body = self._validate_response('Can\'t upload audio', response, validate = lambda body: 'audio' in body)

        return body['audio'], body['server'], body['hash']

    # @retry(times = 3)
    def _save(self, audio: int, server: str, hash_: str, title: str = None, artist: str = None):
        response = post(
            URL_TEMPLATE.format(method = 'audio.save'),
            data = {
                'audio': audio,
                'server': server,
                'hash': hash_,
                'artist': artist,
                'title': title,
                'access_token': self.token,
                'v': self.api_version,
            },
            timeout = TIMEOUT
        )

        body = self._validate_response('Can\'t save uploaded file', response, validate = lambda body: 'response' in body and 'id' in body['response'])
        body_response = body['response']

        return body_response['url'], body_response['id'], body_response['owner_id']

    # @retry(times = 3)
    def _add(self, audio_id: int, owner_id: int):
        response = post(
            URL_TEMPLATE.format(method = 'audio.add'),
            data = {
                'audio_id': audio_id,
                'owner_id': owner_id,
                'group_id': self.audio_owner,
                'access_token': self.token,
                'v': self.api_version
            },
            timeout = TIMEOUT
        )

        body = self._validate_response('Can\'t add uploaded audio to another owner', response, validate = lambda body: 'response' in body)

        return body['response']  # returns audio id

    # @retry(times = 3)
    def _delete(self, audio_id: int, owner_id: int):
        response = post(
            URL_TEMPLATE.format(method = 'audio.delete'),
            data = {
                'audio_id': audio_id,
                'owner_id': owner_id,
                'access_token': self.token,
                'v': self.api_version
            },
            timeout = TIMEOUT
        )

        body = self._validate_response('Can\'t add uploaded audio to another owner', response, validate = lambda body: 'response' in body)

        return body['response']  # returns audio id

    # @retry(times = 3)
    def _add_to_playlist_owner(self, audio_id: int):
        response = post(
            URL_TEMPLATE.format(method = 'audio.add'),
            data = {
                'audio_id': audio_id,
                'owner_id': -self.audio_owner,
                'access_token': self.playlist_token,
                'v': self.api_version
            },
            timeout = TIMEOUT
        )

        body = self._validate_response('Can\'t add uploaded audio to another owner', response, validate = lambda body: 'response' in body)

        return body['response']  # returns audio id

    # @retry(times = 3)
    def _add_to_playlist(self, audio_id: int):
        playlist = self.playlist
        playlist_token = self.playlist_token
        playlist_owner = self.playlist_owner

        data = {
            'audio_ids': f'{-self.audio_owner}_{audio_id}',
            'owner_id': playlist_owner,
            'playlist_id': playlist,
            'access_token': playlist_token,
            'v': self.api_version
        }

        response = post(
            URL_TEMPLATE.format(method = 'audio.addToPlaylist'),
            data = data,
            timeout = TIMEOUT
        )

        # print(response.content)

        body = self._validate_response(
            'Can\'t add uplodaded audio to playlist',
            response,
            validate = lambda body: 'response' in body and len(body['response']) > 0 and 'audio_id' in body['response'][0]
        )

        return body['response'][0]['audio_id']

        # return body['response']  # returns audio id

    # @retry(times = 3)
    # def _add_to_playlist(self, audio_id: int):
    #     playlist = self.playlist
    #     playlist_token = self.playlist_token
    #     playlist_owner = self.playlist_owner

    #     # print(
    #     #     {
    #     #         'audio_ids': [audio_id],
    #     #         # 'owner_id': playlist_owner,  # owner_id,
    #     #         'playlist_id': playlist,
    #     #         'access_token': playlist_token,
    #     #         'v': self.api_version
    #     #     }
    #     # )

    #     # print({
    #     #     'audio_ids': f'{audio_id}',
    #     #     'owner_id': playlist_owner + 1,  # owner_id,
    #     #     'playlist_id': playlist,
    #     #     'access_token': playlist_token,
    #     #     'v': self.api_version
    #     # })

    #     # data = {
    #     #     'owner_id': playlist_owner,  # owner_id,
    #     #     'playlist_id': playlist,
    #     #     'access_token': playlist_token,
    #     #     'v': self.api_version
    #     # }

    #     # # post(
    #     # response = post(
    #     #     URL_TEMPLATE.format(method = 'audio.getPlaylistById'),
    #     #     data = data,
    #     #     timeout = TIMEOUT
    #     # )

    #     # print(response.content)

    #     # return

    #     data = {
    #         'audio_ids': f'{playlist_owner}_{audio_id},{playlist_owner}_456240872',
    #         'owner_id': playlist_owner,  # owner_id,
    #         'playlist_id': playlist,
    #         'access_token': playlist_token,
    #         'v': self.api_version
    #     }

    #     print(data)

    #     # post(
    #     response = post(
    #         URL_TEMPLATE.format(method = 'audio.addToPlaylist'),
    #         data = data,
    #         timeout = TIMEOUT
    #     )

    #     print(response.content)

    #     # body = self._validate_response('Can\'t add uploaded audio to another owner', response, validate = lambda body: 'response' in body)

    #     return audio_id

    #     # return body['response']  # returns audio id

    def upload(self, path: str, title: str = None, artist: str = None, verbose: bool = False):
        # self._add_to_playlist(456240873)

        # self._add_to_playlist_owner(456240868, self.playlist_owner)
        # print(self.audio_owner)
        # self._add_to_playlist_owner(456240001, -224461031)

        # return

        if verbose:
            print('Getting upload url...')

        url = self._get_upload_server()

        if verbose:
            print('Got upload url. Uploading audio...')

        audio, server, hash_ = self._upload(url, path)

        if verbose:
            print('Uploaded audio. Saving audio...')

        url, audio_id, owner_id = self._save(audio, server, hash_, title, artist)

        if verbose:
            print(f'Saved audio as {url}')

        if owner_id != self.audio_owner:
            if verbose:
                print(f'Adding audio to {self.audio_owner}')

            audio_id = self._add(audio_id, owner_id)

            if verbose:
                print(f'Added audio to {self.audio_owner}. Deleting audio from {owner_id}...')

            self._delete(audio_id, owner_id)

            if verbose:
                print(f'Deleted audio from {owner_id}. Adding to playlist {self.playlist}...')

            playlist_audio_id = self._add_to_playlist(audio_id)

            # print(playlist_audio_id)

            # audio_id_for_playlist = self._add_to_playlist_owner(audio_id)
            # self._add_to_playlist(audio_id_for_playlist)

            # self._add_to_playlist(audio_id, owner_id)

            if verbose:
                print(f'Added audio {audio_id} to playlist {self.playlist} as {playlist_audio_id}')

        return audio_id

    @classmethod
    def make(cls):
        token = env.get('MUCH_VK_AUDIO_TOKEN')

        if token is None:
            raise ValueError('vk token in required to upload files')

        token_owner = env.get('MUCH_VK_AUDIO_OWNER')

        if token_owner is None:
            raise ValueError('vk token owner is required to post content')

        community_token = env.get('MUCH_VK_COMMUNITY_TOKEN')

        if community_token is None:
            raise ValueError('vk community token is required to add audios to playlist')

        audio_owner = env.get('MUCH_VK_POST_OWNER')

        if audio_owner is None:
            raise ValueError('vk audio owner is required to post content')

        playlist = env.get('MUCH_VK_PLAYLIST')

        if playlist is None:
            raise ValueError('vk audio playlist is required')

        playlist_token = env.get('MUCH_VK_PLAYLIST_TOKEN')

        if playlist_token is None:
            raise ValueError('vk playlist token is required')

        playlist_owner = env.get('MUCH_VK_PLAYLIST_OWNER')

        if playlist_owner is None:
            raise ValueError('vk playlist owner is required')

        return cls(token, abs(int(token_owner)), abs(int(audio_owner)), int(playlist), community_token, playlist_token, int(playlist_owner))
