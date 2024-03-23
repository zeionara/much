from pathlib import Path
from os import environ as env
from io import BytesIO, BufferedReader

from requests import post as postt, get

from rr.util import is_image, is_video

from .ImageSearchEngine import ImageSearchEngine

from .VkAudioUploader import VkAudioUploader
from .VkFileUploader import VkFileUploader
from .PosterUploader import PosterUploader
from .VkPostUploader import VkPostUploader


TIMEOUT = 3600
N_ATTEMPTS = 3


def make_attachments(audio: int, media_owner: int, poster: int, video: int, doc: int = None):
    if doc is None:
        if video is None:
            return f"audio{media_owner}_{audio},photo{media_owner}_{poster}"
        return f"audio{media_owner}_{audio},video{media_owner}_{video}"

    if video is None:
        return f"audio{media_owner}_{audio},photo{media_owner}_{poster},doc{media_owner}_{doc}"
    return f"audio{media_owner}_{audio},video{media_owner}_{video},doc{media_owner}_{doc}"


class VkClient:
    def __init__(
        self, post_token: str = None, audio_token: str = None,
        post_owner: int = None, audio_owner: int = None,
        post_album: int = None,
        api_version: str = '5.199',
        interactive: bool = False
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

        self.search_engine = ImageSearchEngine()

        self.audio_uploader = VkAudioUploader.make()
        self.file_uploader = VkFileUploader.make(interactive)
        self.poster_uploader = PosterUploader()
        self.post_uploader = VkPostUploader.make()

    def post2(self, audio_path: str, caption: str, artist: str, poster_path: str = None, file_path: int = None, description: str = None, file_tags: list[str] = None, verbose: bool = False):
        audio = self.audio_uploader.upload(audio_path, caption, artist, verbose)

        if poster_path is None:
            poster, poster_type = None, None

            for poster_path_ in self.search_engine.search(caption):
                try:
                    poster, poster_type = self.poster_uploader.upload(poster_path_, caption, description, verbose)
                except ValueError:
                    pass
                else:
                    break
        else:
            poster, poster_type = self.poster_uploader.upload(poster_path, caption, description, verbose)

        if file_path is None:
            file = None
        else:
            file = self.file_uploader.upload(file_path, caption, file_tags, verbose)

        return self.post_uploader.upload(description, audio, file, poster, poster_type, verbose)

    def post(self, path: str, title: str, caption: str, artist: str = None, message: str = None, poster: str = None, file: int = None, verbose: bool = False):
        if verbose:
            print('Uploading audio...')

        # audio = self._upload_audio(path, title, artist)
        audio = self.audio_uploader.upload(path, title, artist)
        # audio = 456239121

        if verbose:
            print(f'Uploaded audio {audio}, creating post...')

        # post_id = self._post(caption, audio, message, poster, verbose)
        post_id = self._post(caption if title is None else title, audio, message, poster, file, verbose)

        if verbose:
            print(f'Created post {post_id}')

        return post_id

    # def _upload_audio(self, path: str, title: str, artist: str = None):
    #     token = self.audio_token
    #     token_owner = self.audio_owner
    #     audio_owner = self.post_owner

    #     api_version = self.api_version

    #     response = postt(
    #         url = 'https://api.vk.com/method/audio.getUploadServer',
    #         data = {
    #             'access_token': token,
    #             'v': api_version
    #         },
    #         timeout = TIMEOUT
    #     )

    #     if response.status_code == 200:
    #         upload_url = response.json()['response']['upload_url']

    #         with open(path, 'rb') as file:
    #             response = postt(
    #                 url = upload_url,
    #                 files = {
    #                     'file': (path, file)
    #                 },
    #                 timeout = TIMEOUT
    #             )

    #         if response.status_code == 200:
    #             response_json = response.json()

    #             if 'audio' not in response_json:
    #                 raise ValueError(f'Missing "audio" field in the response body: {response_json}')

    #             audio = response_json['audio']

    #             server = response_json['server']
    #             hash_ = response_json['hash']

    #             response = postt(
    #                 url = 'https://api.vk.com/method/audio.save',
    #                 data = {
    #                     'access_token': token,
    #                     'audio': audio,
    #                     'server': server,
    #                     'hash': hash_,
    #                     'v': api_version,
    #                     'artist': artist,
    #                     'title': title
    #                 },
    #                 timeout = TIMEOUT
    #             )

    #             if response.status_code == 200:
    #                 response_json = response.json()['response']

    #                 if audio_owner is not None and token_owner != audio_owner:
    #                     response = postt(
    #                         url = 'https://api.vk.com/method/audio.add',
    #                         data = {
    #                             'access_token': token,
    #                             'audio_id': (audio_id := response_json['id']),
    #                             'owner_id': (owner_id := response_json['owner_id']),
    #                             'group_id': abs(audio_owner),
    #                             'v': api_version
    #                         },
    #                         timeout = TIMEOUT
    #                     )

    #                     if response.status_code == 200:
    #                         final_audio_id = response.json().get('response')

    #                         response = postt(
    #                             url = 'https://api.vk.com/method/audio.delete',
    #                             data = {
    #                                 'audio_id': audio_id,
    #                                 'owner_id': owner_id,
    #                                 'access_token': token,
    #                                 'v': api_version
    #                             },
    #                             timeout = TIMEOUT
    #                         )

    #                         if response.status_code == 200:
    #                             # print(response.json())
    #                             return final_audio_id
    #                         raise ValueError(f'Unexpected response from server when deleting audio from the user\'s list: {response.content}')
    #                     raise ValueError(f'Unexpected response from server when adding audio to the group: {response.content}')
    #             raise ValueError(f'Unexpected response from server when saving uploaded audio: {response.content} {response.status_code}')
    #         raise ValueError(f'Unexpected response from server when uploading audio: {response.content}')
    #     raise ValueError(f'Unexpected response from server when obtaining upload url: {response.content}')

    def _post(self, caption: str, audio: int, title: str = None, poster: str = None, doc: int = None, verbose: bool = False, attempt_index: int = 0):
        owner = self.post_owner
        album = self.post_album
        token = self.post_token

        api_version = self.api_version

        poster_is_image = None if poster is None else is_image(poster)
        poster_is_video = None if poster is None else is_video(poster)

        if poster_is_image is False and poster_is_video is False:
            raise ValueError(f'Incorrect poster path: {poster} for thread {caption}')

        if poster_is_video:
            response = postt(
                url = 'https://api.vk.com/method/video.save',
                data = {
                    'name': caption[:128],
                    'description': title[:5000],
                    'repeat': 1,
                    'group_id': abs(owner),
                    'access_token': token,
                    'v': api_version
                },
                timeout = TIMEOUT
            )
        else:
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

            links = self.search_engine.search(caption) if poster is None else [None]

            # if poster is not None:
            #     links = [None, *links]

            for link in links:
                if verbose:
                    print(f'Found poster {link}')

                if poster is None:
                    file = (f'image{Path(link).suffix}', BufferedReader(BytesIO(get(link, timeout = TIMEOUT).content)))
                else:
                    file = open(poster, 'rb')

                response = postt(
                    url = upload_url,
                    files = {
                        'file': file
                    },
                    timeout = TIMEOUT
                )

                if poster is not None:
                    # poster = None
                    file.close()

                if verbose:
                    print(file)

                if response.status_code == 200:
                    response_json = response.json()

                    photos_list = None if poster_is_video else response_json['photos_list']
                    server = None if poster_is_video else response_json['server']
                    hash_ = None if poster_is_video else response_json['hash']

                    if not poster_is_video and len(photos_list) < 1:
                        if attempt_index < N_ATTEMPTS:
                            return self._post(caption, audio, title, poster, doc, verbose, attempt_index + 1)

                        if poster is not None:
                            poster = None

                            poster_is_video = None
                            poster_is_image = None

                            links.extend(self.search_engine.search(caption))
                        continue
                        # raise ValueError('Can\'t upload an image')

                    if not poster_is_video and verbose:
                        print(f'Photos list: {photos_list}')

                    if not poster_is_video:
                        response = postt(
                            url = 'https://api.vk.com/method/photos.save',
                            data = {
                                'group_id': abs(owner),
                                'album_id': album,
                                'server': server,
                                'photos_list': photos_list,
                                'hash': hash_,
                                'caption': caption[:2048] if title is None else title[:2048],
                                'access_token': token,
                                'v': api_version
                            },
                            timeout = TIMEOUT
                        )

                    if poster_is_video or response.status_code == 200:
                        if poster_is_video:
                            video_id = response_json['video_id']
                            photo_id = None
                        else:
                            try:
                                response_json = response.json()['response']
                            except KeyError:
                                if attempt_index < N_ATTEMPTS:
                                    return self._post(caption, audio, title, poster, doc, verbose, attempt_index + 1)

                                if poster is not None:
                                    poster = None

                                    poster_is_video = None
                                    poster_is_image = None

                                    links.extend(self.search_engine.search(caption))
                                continue
                                # raise ValueError(f'Invalid response after saving photos: {response.json()}')

                            photo_id = response_json[0]['id']
                            video_id = None

                        response = postt(
                            url = 'https://api.vk.com/method/wall.post',
                            data = {
                                'owner_id': owner,
                                'from_group': 1,
                                'message': title,
                                'attachments': make_attachments(audio, owner, photo_id, video_id, doc),
                                'access_token': token,
                                'donut_paid_duration': 604800,  # 1 week
                                'v': api_version
                            },
                            timeout = TIMEOUT
                        )

                        if response.status_code == 200:
                            return response.json()['response']['post_id']

                        raise ValueError(f'Unexpected response from server when creating a post: {response.content} for thread {caption}')
                    raise ValueError(f'Unexpected response from server when saving uploaded photo: {response.content} for thread {caption}')

                if attempt_index < N_ATTEMPTS:
                    return self._post(caption, audio, title, poster, doc, verbose, attempt_index + 1)

                if poster is not None:
                    poster = None

                    poster_is_video = None
                    poster_is_image = None

                    links.extend(self.search_engine.search(caption))
                # raise ValueError(f'Unexpected response from server when uploading photo: {response.content}')
            raise ValueError(f'Exhausted {len(links)} poster candidates for thread {caption}')
        raise ValueError(f'Unexpected response from server when obtaining upload url: {response.content} for thread {caption}')
