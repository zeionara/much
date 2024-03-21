from requests import post
from os import environ as env

from .VkUploader import VkUploader, URL_TEMPLATE, TIMEOUT, API_VERSION


class VkFileUploader(VkUploader):
    def __init__(
        self,
        token: str = None,
        owner: int = None,
        api_version: str = API_VERSION
    ):
        self.token = token
        self.owner = owner
        self.api_version = api_version

    # def _validate_response(self, message, response, validate):
    #     if (status_code := response.status_code) != 200 or not validate(body := response.json()):
    #         raise ValueError(f'{message} (status = {status_code}): {body}')

    #     return body

    def _get_upload_server(self):
        response = post(
            URL_TEMPLATE.format(method = 'docs.getUploadServer'),
            data = {
                'access_token': self.token,
                'group_id': self.owner,
                'v': self.api_version
            },
            timeout = TIMEOUT
        )

        body = self._validate_response('Can\'t get upload url', response, validate = lambda body: 'response' in body and 'upload_url' in body['response'])

        return body['response']['upload_url']

    def _upload_file(self, url: str, path: str):
        with open(path, 'r', encoding = 'utf8') as file:
            response = post(
                url,
                files = {
                    'file': file
                },
                timeout = TIMEOUT
            )

        body = self._validate_response('Can\'t upload file', response, validate = lambda body: 'file' in body)

        return body['file']

    def _save(self, file: str, title: str = None, tags: list[str] = None):
        response = post(
            URL_TEMPLATE.format(method = 'docs.save'),
            data = {
                'access_token': self.token,
                'file': file,
                'title': title,
                'tags': tags if tags is None else ','.join(tags),
                'v': self.api_version
            },
            timeout = TIMEOUT
        )

        body = self._validate_response('Can\'t save uploaded file', response, validate = lambda body: 'response' in body and 'doc' in body['response'] and 'url' in body['response']['doc'])

        return body['response']['doc']['url'], body['response']['doc']['id']

    def upload(self, path: str, title: str = None, tags: list[str] = None, verbose: bool = False):
        if verbose:
            print('Getting upload url...')

        url = self._get_upload_server()

        if verbose:
            print('Got upload url. Uploading file...')

        file = self._upload_file(url, path)

        if verbose:
            print('Uploaded file. Saving file...')

        url, id_ = self._save(file, title, tags)

        if verbose:
            print(f'Saved file as {url}')

        return id_

    @classmethod
    def make(cls):
        token = env.get('MUCH_VK_AUDIO_TOKEN')

        if token is None:
            raise ValueError('vk token in required to upload files')

        owner = env.get('MUCH_VK_POST_OWNER')

        if owner is None:
            raise ValueError('vk owner is required to post content')

        return cls(token, abs(int(owner)))
