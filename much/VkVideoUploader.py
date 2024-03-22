from os import environ as env

from requests import post

from .VkUploader import VkUploader, URL_TEMPLATE, TIMEOUT, API_VERSION


class VkVideoUploader(VkUploader):
    def __init__(
        self,
        token: str,
        owner: int,
        api_version: str = API_VERSION
    ):
        self.token = token
        self.owner = owner
        self.api_version = api_version

    def _get_upload_server(self, caption: str, description: str):
        response = post(
            URL_TEMPLATE.format(method = 'video.save'),
            data = {
                'name': caption[:128],
                'description': description[:5000],
                'repeat': 1,
                'group_id': self.owner,
                'access_token': self.token,
                'v': self.api_version
            },
            timeout = TIMEOUT
        )

        body = self._validate_response('Can\'t get url for uploading video', response, validate = lambda body: 'response' in body and 'upload_url' in body['response'])

        return body['response']['upload_url']

    def _upload(self, url: str, path: str):
        with open(path, 'rb') as file:
            response = post(
                url,
                files = {
                    'file': file
                },
                timeout = TIMEOUT
            )

        body = self._validate_response('Can\'t upload video', response, validate = lambda body: 'video_id' in body and 'owner_id' in body and 'direct_link' in body)

        return body['direct_link'], body['video_id'], body['owner_id']

    def upload(self, path: str, caption: str, description: str, verbose: bool = False):
        if verbose:
            print('Getting upload url...')

        url = self._get_upload_server(caption, description)

        if verbose:
            print('Got upload url. Uploading video...')

        url, video_id, _ = self._upload(url, path)

        if verbose:
            print(f'Uploaded as {url}')

        return video_id

    @classmethod
    def make(cls):
        token = env.get('MUCH_VK_POST_TOKEN')

        if token is None:
            raise ValueError('vk token in required to upload files')

        owner = env.get('MUCH_VK_POST_OWNER')

        if owner is None:
            raise ValueError('vk post owner is required to post content')

        return cls(token, abs(int(owner)))
