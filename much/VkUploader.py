from abc import ABC

URL_TEMPLATE = 'https://api.vk.com/method/{method}'

TIMEOUT = 3600

API_VERSION = '5.199'


class VkUploader(ABC):
    def _validate_response(self, message, response, validate, get_body = None):
        if (status_code := response.status_code) != 200 or not validate(body := (response.json() if get_body is None else get_body(response.json()))):
            raise ValueError(f'{message} (status = {status_code}): {body}')

        return body

    # def _validate_props(self, message, response, props: list[str], validate = None, get_body = None):
    #     body = self._validate_response(message, response, lambda body: validate is None or validate(body) all(prop in body for prop in props), get_body)

    #     return tuple(body[prop] for prop in props)

    # def _validate_prop(self, message, response, prop: str, get_body = None):
    #     body = self._validate_response(message, response, lambda body: prop in body, get_body)

    #     return body[prop]

    # def _validate_response_props(self, message, response, props: list[str]):
    #     return self._validate_props(message, response, props, get_body = lambda body: body['response'])
