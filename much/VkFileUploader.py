from requests import post
from os import environ as env

from rr.util import retry
from .util import post as post_handling_captcha

from .VkUploader import VkUploader, URL_TEMPLATE, TIMEOUT, API_VERSION

# CAPTCHA_ERROR_CODE = 14

# def postt(self, url: str, data: dict, timeout: int = None, interactive: bool = True):
#     def get_response(captcha_key: str = None, captcha_sid: str = None):
#         if captcha_key is not None and captcha_sid is not None:
#             data_ = dict(data)
#
#             data_['captcha_key'] = captcha_key
#             data_['captcha_sid'] = captcha_sid
#         else:
#             data_ = data
#
#         return post(url, data = data_, timeout = timeout)
#
#     response = get_response()
#
#     if response.status_code == 200 and interactive:
#         response_json = response.json()
#
#         if (error := response_json.get('error')) is not None and error.get('error_code') == CAPTCHA_ERROR_CODE:
#             print(f'Captcha needed: {error.get("captcha_img")}')
#             captcha_key = input('> ')
#
#             response = get_response(captcha_key, error.get('captcha_sid'))
#
#     return response


class VkFileUploader(VkUploader):
    def __init__(
        self,
        token: str = None,
        owner: int = None,
        api_version: str = API_VERSION,
        interactive: bool = False
    ):
        self.token = token
        self.owner = owner
        self.api_version = api_version
        self.interactive = interactive

    # def _validate_response(self, message, response, validate):
    #     if (status_code := response.status_code) != 200 or not validate(body := response.json()):
    #         raise ValueError(f'{message} (status = {status_code}): {body}')

    #     return body

    @retry(times = 3)
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

    @retry(times = 3)
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

    @retry(times = 3)
    def _save(self, file: str, title: str = None, tags: list[str] = None):
        response = post_handling_captcha(
            URL_TEMPLATE.format(method = 'docs.save'),
            data = {
                'file': file,
                'title': title,
                'tags': tags if tags is None else ','.join(tags),
                'access_token': self.token,
                'v': self.api_version
            },
            timeout = TIMEOUT,
            interactive = self.interactive
        )

        # def get_response(captcha_key: str = None, captcha_sid: str = None):
        #     data = {
        #         'access_token': self.token,
        #         'file': file,
        #         'title': title,
        #         'tags': tags if tags is None else ','.join(tags),
        #         'v': self.api_version
        #     }

        #     if captcha_key is not None and captcha_sid is not None:
        #         data['captcha_key'] = captcha_key
        #         data['captcha_sid'] = captcha_sid

        #     return post(URL_TEMPLATE.format(method = 'docs.save'), data = data, timeout = TIMEOUT)

        # response = get_response()

        # if response.status_code == 200:
        #     response_json = response.json()

        #     if (error := response_json.get('error')) is not None and error.get('error_code') == 14:
        #         print(f'Captcha needed: {error.get("captcha_img")}')
        #         captcha_key = input('> ')

        #         response = get_response(captcha_key, error.get('captcha_sid'))

        body = self._validate_response('Can\'t save uploaded file', response, validate = lambda body: 'response' in body and 'doc' in body['response'] and 'url' in body['response']['doc'])

        return body['response']['doc']['url'], body['response']['doc']['id']

    def upload(self, path: str, title: str = None, tags: list[str] = None, verbose: bool = False):
        if verbose:
            print('Getting file upload url...')

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
    def make(cls, interactive: bool = False):
        token = env.get('MUCH_VK_AUDIO_TOKEN')

        if token is None:
            raise ValueError('vk token in required to upload files')

        owner = env.get('MUCH_VK_POST_OWNER')

        if owner is None:
            raise ValueError('vk owner is required to post content')

        return cls(token, abs(int(owner)), interactive = interactive)
