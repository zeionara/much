from os import environ as env
from time import sleep

from requests import post

WAITING_INTERVAL = 60
N_ATTEMPTS = 5


class HuggingFaceClient:
    def __init__(self, model: str = 'IlyaGusev/rut5_base_headline_gen_telegram', token: str = None):
        if token is None:
            token = env.get('HUGGING_FACE_INFERENCE_API_TOKEN')

            if token is None:
                raise ValueError('Huggingface api token is required')

        self.token = token
        self.model = model

        self.url = f'https://api-inference.huggingface.co/models/{model}'
        self.headers = {
            'Authorization': f'Bearer {token}'
        }

    def summarize(self, text: str, verbose: bool = False):
        n_attempts = 0
        while True:
            response = post(self.url, headers = self.headers, json = text)

            if response.status_code == 200:
                return response.json()[0]['summary_text']
            elif response.status_code == 503:
                response_json = response.json()

                if (estimated_time := response_json.get('estimated_time')) is not None:
                    if verbose:
                        print(f'The model is loading. Waiting for {estimated_time} seconds before proceeding...')
                    sleep(estimated_time)
                    if verbose:
                        print('Proceeding...')
                else:
                    if n_attempts > N_ATTEMPTS:
                        raise ValueError(f'Unexpected error format: {response_json}')
                    else:
                        n_attempts += 1
                        sleep(WAITING_INTERVAL)
            else:
                if n_attempts > N_ATTEMPTS:
                    raise ValueError(f'Unexpected response status code: {response.status_code}')
                else:
                    n_attempts += 1
                    sleep(WAITING_INTERVAL)
