from os import environ as env

from requests import post

from .VkUploader import VkUploader, URL_TEMPLATE, TIMEOUT, API_VERSION
from .PosterUploader import AttachmentType


class VkPostUploader(VkUploader):
    def __init__(
        self,
        token: str,
        owner: int,
        api_version: str = API_VERSION
    ):
        self.token = token
        self.owner = owner
        self.api_version = api_version

    def _upload(self, title: str, attachments: str):
        response = post(
            URL_TEMPLATE.format(method = 'wall.post'),
            data = {
                'owner_id': self.owner,
                'from_group': 1,
                'message': title,
                'attachments': attachments,
                'access_token': self.token,
                'donut_paid_duration': 604800,  # 1 week
                'v': self.api_version
            },
            timeout = TIMEOUT
        )

        body = self._validate_response('Can\'t create post', response, validate = lambda body: 'response' in body and 'post_id' in body['response'])

        return body['response']['post_id']

    def upload(self, title: str, audio: int, document: int, poster: int, poster_type: AttachmentType, verbose: bool = False):
        if verbose:
            print('Making post...')

        owner = self.owner

        attachments = []

        if audio is not None:
            attachments.append(AttachmentType.AUDIO.encode(owner, audio))

        if document is not None:
            attachments.append(AttachmentType.DOCUMENT.encode(owner, document))

        if poster is not None and poster_type is not None:
            attachments.append(poster_type.encode(owner, poster))

        post_id = self._upload(title, ','.join(attachments))

        if verbose:
            print(f'Posted as {post_id}')

        return post_id

    @classmethod
    def make(cls):
        token = env.get('MUCH_VK_POST_TOKEN')

        if token is None:
            raise ValueError('vk token in required to upload files')

        owner = env.get('MUCH_VK_POST_OWNER')

        if owner is None:
            raise ValueError('vk post owner is required to post content')

        return cls(token, int(owner))
